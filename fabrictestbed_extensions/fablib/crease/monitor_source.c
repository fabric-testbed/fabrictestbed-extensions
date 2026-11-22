/* SPDX-License-Identifier: BSD-3-Clause
 * Copyright(c) 2010-2015 Intel Corporation
 */
#define _POSIX_C_SOURCE 199309L
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <inttypes.h>
#include <arpa/inet.h>
#include <sys/time.h>

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_cycles.h>
#include <rte_lcore.h>
#include <rte_mbuf.h>
#include <rte_malloc.h>
#include <rte_ring.h>
#include <rte_soring.h>

#define NUM_MBUFS 8192*2
#define MBUF_CACHE_SIZE 128
#define BURST_SIZE 128
#define MIN_REPLAY_SIZE 128
#define REPLAY_TX_RETRIES 4
#define BURST_TX_DRAIN_US 1 /* TX drain every ~1us */
/* Configure how many packets ahead to prefetch, when reading packets */
#define PREFETCH_OFFSET	3
//#define CRINKLE_DEBUG 1

/* allow max jumbo frame 9.5 KB */
#define	JUMBO_FRAME_MAX_SIZE	0x2600
#define MAX_RX_MTU 1500

#define	PKT_MBUF_DATA_SIZE	RTE_MBUF_DEFAULT_BUF_SIZE

#define NSEC_PER_SEC        1000000000L

#define MONPROT 0x6587
#define CREASEPROT 254
#define CREASEVER "Crease Monitor v0.6.2\n"

#define MAX_PORTS 3

static uint64_t tsc_hz;

static inline uint64_t timespec64_to_ns(const struct timespec *ts)
{
	return ((uint64_t) ts->tv_sec * NSEC_PER_SEC) + ts->tv_nsec;
}

unsigned char ana_headers[64];
// Ether(14) + IPv6(40) + len(2) + 2xUID(32)
const uint16_t ana_size = 88;
uint64_t mon_id;
uint16_t nb_ports;
unsigned nb_lcores, rx_lcores[MAX_PORTS], max_replay_size, nb_worker_cores, worker_core_ids[RTE_MAX_LCORE];
static struct rte_mempool *packet_pool, *clone_pool, *replay_pool;
static struct rte_ring *replay_rings[MAX_PORTS - 1];
static struct rte_soring *packet_rings[MAX_PORTS - 1];

//static int rx_queue_per_lcore = 1;

#define RX_RING_SIZE 1024
#define TX_RING_SIZE 4096
static uint16_t nb_rxd = RX_RING_SIZE;
static uint16_t nb_txd = TX_RING_SIZE;
static struct rte_ether_addr ports_eth_addr[MAX_PORTS];

static uint16_t vport_to_devport[MAX_PORTS];
static uint16_t devport_to_vport[MAX_PORTS];

struct packet_metadata {
	uint64_t systime_ns;
	union {
		int rc;
		struct {
			uint16_t port;
			uint16_t queue;
		} tx;
	} tx_state;
};

ssize_t testsize = sizeof(struct packet_metadata);

struct __rte_cache_aligned replay_buf {
	uint32_t len;
	uint64_t tsc;
	struct rte_mbuf *bufs[BURST_SIZE];
};

static struct replay_buf **replay_run_bufs[MAX_PORTS - 1];
static uint64_t record_pkts[MAX_PORTS - 1];
static uint64_t record_drops[MAX_PORTS - 1];

struct tlr_struct {
	uint64_t systime_ns;
	uint64_t trailer;
};

struct lcore_args {
	uint16_t port_id;
	uint16_t queue_id;
};
static struct lcore_args args[RTE_MAX_LCORE];

static inline uint64_t
extract_long(uint8_t* ptr)
{
	return ((uint64_t)ptr[0] << 56) |
		   ((uint64_t)ptr[1] << 48) |
		   ((uint64_t)ptr[2] << 40) |
		   ((uint64_t)ptr[3] << 32) |
		   ((uint64_t)ptr[4] << 24) |
		   ((uint64_t)ptr[5] << 16) |
		   ((uint64_t)ptr[6] << 8) |
		   ((uint64_t)ptr[7]);
}

#define TYPE_REPLAY_RECORD (uint8_t)1
#define TYPE_REPLAY_CLEAR (uint8_t)2
#define TYPE_REPLAY_RUN (uint8_t)4
#define IDX_REPLAY_RECORD (uint8_t)0
#define IDX_REPLAY_CLEAR (uint8_t)1
#define IDX_REPLAY_RUN (uint8_t)2
bool do_run = true;
uint8_t c_to_tx[RTE_MAX_LCORE];
uint8_t tx_to_c[RTE_MAX_LCORE];
uint16_t c_ctrs[8];
uint64_t replay_start = 0;
uint64_t replay_end = 0;
uint64_t replay_run_start = 0;

static struct rte_eth_conf port_conf = {
	.rxmode = {
		.mtu = MAX_RX_MTU,
	},
	.txmode = {},
};

static void
print_ethaddr(const char *name, struct rte_ether_addr *eth_addr)
{
	char buf[RTE_ETHER_ADDR_FMT_SIZE];
	rte_ether_format_addr(buf, RTE_ETHER_ADDR_FMT_SIZE, eth_addr);
	printf("%s%s", name, buf);
}

static void
signal_handler(int signum)
{
	if (signum == SIGINT || signum == SIGTERM) {
		printf("\n\nSignal %d received, preparing to exit...\n",
				signum);
		do_run = false;
	}
}

static inline void
debug_printf(const char *fmt, ...)
{
	#ifdef CRINKLE_DEBUG
	va_list args;
	va_start(args, fmt);
	vprintf(fmt, args);
	va_end(args);
	#endif
}

static inline void
send_burst_replayable(
	struct rte_mbuf **bufs,
	const uint64_t systime_ns,
	const uint64_t copy_replay_start,
	const uint64_t copy_replay_end,
	const uint16_t outport,
	const uint16_t queueid,
	const uint16_t pidx,
	const uint16_t nb_rx)
{
	struct replay_buf *rbuf;
	uint64_t tx_tsc = 0;
	uint16_t nb_tx;
	const bool recording = systime_ns <= copy_replay_end && systime_ns >= copy_replay_start;

	// Stamp before the TX call so a replayed burst, which waits for the stored
	// TSC and then calls TX, reproduces the same reference point
	if (unlikely(recording))
		tx_tsc = rte_rdtsc_precise();
	nb_tx = rte_eth_tx_burst(outport, queueid, bufs, nb_rx);
	if (unlikely(nb_tx < nb_rx)) {
		rte_pktmbuf_free_bulk(&bufs[nb_tx], nb_rx - nb_tx);
		debug_printf("Failed to send all packets, sent %d, total %d\n", nb_tx, nb_rx);
	}

	if (unlikely(recording)) {
		if (unlikely(rte_mempool_get(replay_pool, (void **)&rbuf) < 0)) {
			debug_printf("No replay bufs left, not storing packets\n");
			record_drops[pidx] += nb_rx;
			rte_pktmbuf_free_bulk(bufs, nb_rx);
			rte_pktmbuf_free_bulk(bufs, nb_rx);
			return;
		}
		rbuf->tsc = tx_tsc;
		rbuf->len = nb_tx;
		rte_memcpy(rbuf->bufs, bufs, nb_tx * sizeof(struct rte_mbuf *));
		if (unlikely(rte_ring_enqueue(replay_rings[pidx], rbuf) != 0)) {
			debug_printf("Replay buffer overflow, not storing packets\n");
			record_drops[pidx] += nb_rx;
			rte_mempool_put(replay_pool, rbuf);
			rte_pktmbuf_free_bulk(bufs, nb_rx);
			rte_pktmbuf_free_bulk(bufs, nb_rx);
			return;
		}
		record_pkts[pidx] += nb_tx;
		// Packets the TX burst did not send are not stored, so drop the two
		// references that would otherwise be held for replay
		if (unlikely(nb_tx < nb_rx)) {
			rte_pktmbuf_free_bulk(&bufs[nb_tx], nb_rx - nb_tx);
			rte_pktmbuf_free_bulk(&bufs[nb_tx], nb_rx - nb_tx);
		}
	}
	else {
		// Double free since the refcnt will be at +2
		rte_pktmbuf_free_bulk(bufs, nb_rx);
		rte_pktmbuf_free_bulk(bufs, nb_rx);
	}
}

/* Get the output devport of input vport */
static inline uint16_t
get_output_port_from_vport(uint16_t input_port) {
	if (input_port == 1) return vport_to_devport[2];
	return vport_to_devport[1];
}

static void
clear_replay(const uint16_t pidx)
{
	struct replay_buf *rbuf;
	uint64_t bursts = 0;
	while (rte_ring_dequeue(replay_rings[pidx], (void **)&rbuf) == 0) {
		// Double free since stored packets hold two references
		rte_pktmbuf_free_bulk(rbuf->bufs, rbuf->len);
		rte_pktmbuf_free_bulk(rbuf->bufs, rbuf->len);
		rte_mempool_put(replay_pool, rbuf);
		++bursts;
	}
	printf("REPLAY-CLEAR port %hu: freed %lu bursts, had stored %lu pkts, dropped %lu\n",
		   pidx, bursts, record_pkts[pidx], record_drops[pidx]);
	record_pkts[pidx] = 0;
	record_drops[pidx] = 0;
}

static void
run_replay(
	const uint16_t pidx,
	const uint16_t outport,
	const uint16_t queueid,
	const uint64_t start_time)
{
	struct replay_buf **rbufs = replay_run_bufs[pidx];
	struct replay_buf *rbuf;
	uint64_t delta_ns, tsc_delta, tsc_target, curr;
	uint64_t late = 0, worst_late = 0, sent_pkts = 0, lost_pkts = 0;
	uint32_t n, i, j;
	uint16_t nb_tx;

	n = rte_ring_dequeue_burst(replay_rings[pidx], (void **)rbufs, max_replay_size, NULL);
	if (unlikely(n == 0)) return;

	// Split the conversion to avoid overflowing delta_ns * tsc_hz
	delta_ns = start_time - replay_start;
	tsc_delta = (delta_ns / NSEC_PER_SEC) * tsc_hz
			+ ((delta_ns % NSEC_PER_SEC) * tsc_hz) / NSEC_PER_SEC;

	for (i = 0; i < n; ++i) {
		rbuf = rbufs[i];
		tsc_target = rbuf->tsc + tsc_delta;
		curr = rte_rdtsc_precise();
		if (unlikely(curr > tsc_target)) {
			++late;
			if (curr - tsc_target > worst_late)
				worst_late = curr - tsc_target;
		}
		else {
			while (rte_rdtsc_precise() < tsc_target)
				;
		}
		nb_tx = rte_eth_tx_burst(outport, queueid, rbuf->bufs, (uint16_t)rbuf->len);
		for (uint16_t tries = 0; tries < REPLAY_TX_RETRIES && nb_tx < rbuf->len; ++tries) {
			nb_tx += rte_eth_tx_burst(outport, queueid, &rbuf->bufs[nb_tx],
									  (uint16_t)(rbuf->len - nb_tx));
		}
		sent_pkts += nb_tx;
		if (unlikely(nb_tx < rbuf->len)) {
			lost_pkts += rbuf->len - nb_tx;
			rte_pktmbuf_free_bulk(&rbuf->bufs[nb_tx], rbuf->len - nb_tx);
		}
	}
	printf("REPLAY-RUN port %hu: %u bursts, %lu pkts sent, %lu pkts lost, %lu late bursts, worst %lu ns\n",
		   pidx, n, sent_pkts, lost_pkts, late, worst_late * NSEC_PER_SEC / tsc_hz);
	// Does the refcnt update second so that replay can happen immediately,
	// then requeues the bursts in order so the recording can be replayed again
	for (i = 0; i < n; ++i) {
		for (j = 0; j < rbufs[i]->len; ++j) {
			rte_pktmbuf_refcnt_update(rbufs[i]->bufs[j], 1);
		}
	}
	rte_ring_enqueue_burst(replay_rings[pidx], (void **)rbufs, n, NULL);
}

/* IPv6 neighbor discovery on the analyzer port (vport 0) only. The analyzer, or the
 * FABNet router in front of a monitor at another site, resolves the monitor's
 * analyzer-network address before sending it commands, and the DPDK port has no kernel
 * behind it to answer. The data ports never answer, keeping the monitor transparent. */
#define ICMPV6_NH 58
#define ND_NEIGHBOR_SOLICIT 135
#define ND_NEIGHBOR_ADVERT 136
#define ND_OPT_TARGET_LLADDR 2
/* TX queue of the analyzer port reserved for the main lcore's advertisements; the
 * workers own queues 0..nb_worker_cores-1. */
static uint16_t nd_txq;

static uint16_t
icmpv6_checksum(const uint8_t *src, const uint8_t *dst, const uint8_t *msg, uint16_t len)
{
	uint32_t sum = 0;
	uint16_t i;
	for (i = 0; i < 16; i += 2)
		sum += (src[i] << 8 | src[i + 1]) + (dst[i] << 8 | dst[i + 1]);
	sum += len + ICMPV6_NH;
	for (i = 0; i + 1 < len; i += 2)
		sum += msg[i] << 8 | msg[i + 1];
	if (len & 1)
		sum += msg[len - 1] << 8;
	while (sum >> 16)
		sum = (sum & 0xffff) + (sum >> 16);
	return (uint16_t)~sum;
}

/* If buf is a Neighbor Solicitation for this monitor's address (ana_headers[22..37]),
 * send the Neighbor Advertisement and return 1; otherwise return 0. */
static int
crinkle_nd_reply(struct rte_mbuf *buf, const uint16_t portid)
{
	static const uint8_t all_nodes[16] = {0xff, 0x02, [15] = 0x01};
	static const uint8_t unspecified[16] = {0};
	const uint8_t *p = rte_pktmbuf_mtod(buf, const uint8_t *);
	const uint8_t *ip = p + 14, *icmp = p + 54;
	const uint8_t *my_ip = &ana_headers[22];
	const uint8_t *my_mac = ports_eth_addr[portid].addr_bytes;
	struct rte_mbuf *na;
	uint8_t *q, *qi, *qc;
	uint16_t cksum;
	int solicited;

	if (rte_pktmbuf_data_len(buf) < 14 + 40 + 24)
		return 0;
	if (p[12] != 0x86 || p[13] != 0xDD || ip[6] != ICMPV6_NH || ip[7] != 255)
		return 0;
	if (icmp[0] != ND_NEIGHBOR_SOLICIT || icmp[1] != 0 || memcmp(icmp + 8, my_ip, 16) != 0)
		return 0;

	na = rte_pktmbuf_alloc(packet_pool);
	if (na == NULL)
		return 1;
	q = (uint8_t *)rte_pktmbuf_append(na, 14 + 40 + 32);
	if (q == NULL) {
		rte_pktmbuf_free(na);
		return 1;
	}
	/* A solicitation from the unspecified address (duplicate address detection) is
	 * answered to all nodes, unsolicited. */
	solicited = memcmp(ip + 8, unspecified, 16) != 0;
	rte_memcpy(q, p + 6, 6);
	rte_memcpy(q + 6, my_mac, 6);
	q[12] = 0x86;
	q[13] = 0xDD;
	qi = q + 14;
	memset(qi, 0, 8);
	qi[0] = 0x60;
	qi[5] = 32;
	qi[6] = ICMPV6_NH;
	qi[7] = 255;
	rte_memcpy(qi + 8, my_ip, 16);
	rte_memcpy(qi + 24, solicited ? ip + 8 : all_nodes, 16);
	qc = qi + 40;
	memset(qc, 0, 32);
	qc[0] = ND_NEIGHBOR_ADVERT;
	qc[4] = solicited ? 0x60 : 0x20; /* Solicited and Override flags */
	rte_memcpy(qc + 8, my_ip, 16);
	qc[24] = ND_OPT_TARGET_LLADDR;
	qc[25] = 1;
	rte_memcpy(qc + 26, my_mac, 6);
	cksum = icmpv6_checksum(qi + 8, qi + 24, qc, 32);
	qc[2] = cksum >> 8;
	qc[3] = cksum & 0xff;
	if (rte_eth_tx_burst(portid, nd_txq, &na, 1) == 0)
		rte_pktmbuf_free(na);
	return 1;
}

static inline void
crinkle_command_handler(
	struct rte_mbuf *buf,
	const uint64_t systime_ns)
{
	uint8_t* cursor = rte_pktmbuf_mtod_offset(buf, uint8_t*, 12);
	unsigned i;
	if (*cursor != 0x86 || *(cursor + 1) != 0xDD) return;
	cursor += 2 + 6;
	if (*cursor != CREASEPROT) return;
	cursor += 2 + 32;

	if (*cursor == TYPE_REPLAY_RECORD) {
		printf("Replay record command received\n");
		replay_start = extract_long(++cursor);
		cursor += 8;
		replay_end = extract_long(cursor);
		printf("Replay record start: %lu, end: %lu\n", replay_start, replay_end);
	}
	else if (*cursor == TYPE_REPLAY_CLEAR) {
		printf("Replay clear command received\n");
		// if c_ctrs is > 0, that means one or more rx lcores have not finished
		// handling the last command
		if (unlikely(c_ctrs[IDX_REPLAY_CLEAR] > 0)) return;
		if (unlikely(c_ctrs[IDX_REPLAY_RUN] > 0)) return;
		replay_end = 0;
		for (i = 1; i < nb_ports; ++i) {
			__atomic_fetch_or(&c_to_tx[rx_lcores[i]], TYPE_REPLAY_CLEAR, __ATOMIC_RELEASE);
		}
		c_ctrs[IDX_REPLAY_CLEAR] = nb_ports - 1;
		printf("Clearing replay buffers\n");
	}
	else if (*cursor == TYPE_REPLAY_RUN) {
		printf("Replay run command received\n");
		if (unlikely(replay_end == 0 || systime_ns < replay_end)) return;
		if (unlikely(c_ctrs[IDX_REPLAY_CLEAR] > 0)) return;
		if (unlikely(c_ctrs[IDX_REPLAY_RUN] > 0)) return;
		replay_run_start = extract_long(++cursor);
		if (unlikely(replay_run_start <= replay_start)) {
			printf("Replay run start %lu predates recording start %lu, ignoring\n",
				   replay_run_start, replay_start);
			return;
		}
		for (i = 1; i < nb_ports; ++i) {
			__atomic_fetch_or(&c_to_tx[rx_lcores[i]], TYPE_REPLAY_RUN, __ATOMIC_RELEASE);
		}
		c_ctrs[IDX_REPLAY_RUN] = nb_ports - 1;
		printf("Replay run start: %lu\n", replay_run_start);
	}
}

/**
 * This function handles adding (if needed) the custom trailer that stores the packet UID.
 * The UID is formed as:
 * 0                 64       80         96          112       128
 * | timestamp in ns | mon_id | port num | frame len | MONPROT |
 * Additionally, this function crafts the packet that goes to the analyzer, which is formed as
 * 0				54           56                64       66        68    70    72
 * | ethernet + ip6 | packet len | timestamp in ns | mon_id | port_id | res | res |
 * 72            80
 * | UID trailer | 80 bytes of header stack |
 */

static inline void
crinkle_process_burst(
	struct rte_mbuf **bufs,
	struct rte_mbuf **cbufs,
	struct packet_metadata *metas,
	const unsigned char *local_ana_headers,
	const uint16_t vport,
	const uint16_t nb_rx,
	const uint16_t outport,
	const uint16_t queue_id)
{
	struct rte_mbuf *buf, *cbuf;
	struct tlr_struct s_tlr;
	uint32_t *cand_tlr_ptr, cand_tlr, ts_lower;
	uint16_t i, nb_tx, pkt_size, c_ctr;
	uint8_t *tlr, *c;

	c_ctr = 0;
	for (i = 0; i < nb_rx; ++i) {
		buf = bufs[i];
		cand_tlr_ptr = rte_pktmbuf_mtod_offset(buf, uint32_t*, buf->data_len-4);
		cand_tlr = rte_be_to_cpu_32(*cand_tlr_ptr);
		ts_lower = rte_be_to_cpu_32(*(cand_tlr_ptr - 2));
		s_tlr.systime_ns = rte_cpu_to_be_64(metas[i].systime_ns);
		s_tlr.trailer = rte_cpu_to_be_64((mon_id << 48) | ((uint64_t)(vport) << 32) | (((metas[i].systime_ns << 16) & 0x00000000FFFF0000) | MONPROT));

		// Check for existing UUID trailer
		// TODO: FIX THAT THIS IS BACKWARDS
		if ((cand_tlr & 0x0000FFFF) != MONPROT || (cand_tlr >> 16) != (ts_lower & 0x0000FFFF)) {
			if (unlikely((tlr = (uint8_t *)rte_pktmbuf_append(buf, 16)) == NULL)) {
				debug_printf("Failed to append trailer to packet\n");
				metas[i].tx_state.rc = -1;
				continue;
			}
			rte_mov16(tlr, (uint8_t *)(&s_tlr));
		}
		rte_pktmbuf_refcnt_update(buf, 2);
		
		if (unlikely ((cbuf = rte_pktmbuf_clone(buf, clone_pool)) == NULL)) {
			debug_printf("Failed to clone packet for analyzer, populated: %u\n", clone_pool->populated_size);
			continue;
		}
		if (unlikely((c = (uint8_t*)rte_pktmbuf_prepend(cbuf, 88)) == NULL)) {
			debug_printf("Failed to prepend clone packet\n");
			rte_pktmbuf_free(cbuf);
			continue;
		}
		pkt_size = rte_cpu_to_be_16(buf->data_len);
		rte_mov64(c, local_ana_headers);
		rte_mov15_or_less(c+54, (uint8_t *)(&pkt_size), 2);
		rte_mov16(c+56, (uint8_t *)(&s_tlr));
		rte_mov16(c+72, rte_pktmbuf_mtod_offset(buf, uint8_t*, buf->data_len-16));
		cbufs[c_ctr++] = cbuf;
	}

	// TODO: Evaluate doing this in crinkle_rx instead
	nb_tx = rte_eth_tx_burst(outport, queue_id, cbufs, c_ctr);
	if (unlikely(nb_tx < c_ctr)) {
		debug_printf("Failed to send all analyzer packets, sent %d, total %d\n", nb_tx, c_ctr);
		rte_pktmbuf_free_bulk(&cbufs[nb_tx], c_ctr - nb_tx);
	}
}

static int
crinkle_tx(
	void *void_arg)
{
	struct rte_mbuf *bufs[BURST_SIZE/2];
	struct rte_mbuf *cbufs[BURST_SIZE/2];
	struct packet_metadata metas[BURST_SIZE/2];
	unsigned char local_ana_headers[64];
	uint32_t n;
	uint32_t ftoken;
	uint16_t vport;
	const struct lcore_args *arg = (const struct lcore_args *)void_arg;
	const uint16_t port_id = arg->port_id;
	const uint16_t queue_id = arg->queue_id;
	printf("Starting crinkle on port %hu, queue %hu\n", port_id, queue_id);

	rte_mov64(local_ana_headers, ana_headers);

	while (do_run) {
		for (vport = 1; vport < nb_ports; ++vport) {
			n = rte_soring_acquirx_burst(packet_rings[vport-1], bufs, metas, 0, BURST_SIZE/2, &ftoken, NULL);
			if (n > 0) {
				crinkle_process_burst(bufs, cbufs, metas, local_ana_headers, vport, n, port_id, queue_id);
				// NULL for bufs since the actual pointers aren't changed
				rte_soring_releasx(packet_rings[vport-1], NULL, metas, 0, n, ftoken);
			}
		}
	}

	return 0;
}

static int
crinkle_rx(
	void *void_arg)
{
	struct rte_mbuf *bufs[BURST_SIZE];
	struct packet_metadata default_metas[BURST_SIZE];
	struct packet_metadata metas[BURST_SIZE];
	struct timespec ts;
	const struct lcore_args *arg = (const struct lcore_args *)void_arg;
	const uint16_t port_id = arg->port_id;
	const uint16_t queue_id = arg->queue_id;
	const uint16_t vport = devport_to_vport[port_id];
	const uint16_t pidx = vport - 1;
	const uint16_t outport = get_output_port_from_vport(vport);
	const unsigned lcore_id = rte_lcore_id();
	uint64_t systime_ns;
	uint32_t n, nb_rx, nb_rem = 0, nb_warn;
	uint16_t i;

	clock_gettime(CLOCK_REALTIME, &ts);
	systime_ns = timespec64_to_ns(&ts);

	for (i = 0; i < BURST_SIZE; ++i) {
		default_metas[i].systime_ns = 0;
		default_metas[i].tx_state.tx.port = vport;
		default_metas[i].tx_state.tx.queue = 0;
	}

	nb_warn = (nb_ports - 1) * NUM_MBUFS * 0.8;
	debug_printf("Warn at %u packets pending processing\n", nb_warn);
	while(do_run) {
		nb_rx = rte_eth_rx_burst(port_id, 0, bufs, BURST_SIZE);
		if (nb_rx > 0) {
			/* Get time for packet trailers*/
			clock_gettime(CLOCK_REALTIME, &ts);
			systime_ns = timespec64_to_ns(&ts);
			for (i = 0; i < nb_rx; ++i) {
				default_metas[i].systime_ns = systime_ns + i;
			}

			/* Enqueue */
			
			n = rte_soring_enqueux_burst(packet_rings[pidx], bufs, default_metas, nb_rx, NULL);
			if (unlikely(n < nb_rx)) {
				debug_printf("Warning: packet ring full, dropping %u packets\n", nb_rx - n);
				rte_pktmbuf_free_bulk(&bufs[n], nb_rx - n);
			}
		}
		else if (unlikely(replay_end != 0)) {
			clock_gettime(CLOCK_REALTIME, &ts);
			systime_ns = timespec64_to_ns(&ts);
		}

		/* Dequeue and Transmit */
		
		n = rte_soring_dequeux_burst(packet_rings[pidx], bufs, metas, BURST_SIZE, &nb_rem);
		if (nb_rem > nb_warn) {
			debug_printf("Warning: too many packets pending processing (%u)\n", nb_rem);
		}
		
		if (n > 0) {
			send_burst_replayable(bufs, systime_ns, replay_start, replay_end,
									outport, queue_id, pidx, n);
		}

		uint8_t cmds = __atomic_load_n(&c_to_tx[lcore_id], __ATOMIC_ACQUIRE);
		if (unlikely(cmds)) {
			if (cmds & TYPE_REPLAY_CLEAR) {
				clear_replay(pidx);
				__atomic_fetch_and(&c_to_tx[lcore_id], (uint8_t)~TYPE_REPLAY_CLEAR, __ATOMIC_RELEASE);
				__atomic_fetch_or(&tx_to_c[lcore_id], TYPE_REPLAY_CLEAR, __ATOMIC_RELEASE);
			}
			else if (cmds & TYPE_REPLAY_RUN) {
				run_replay(pidx, outport, queue_id, replay_run_start);
				__atomic_fetch_and(&c_to_tx[lcore_id], (uint8_t)~TYPE_REPLAY_RUN, __ATOMIC_RELEASE);
				__atomic_fetch_or(&tx_to_c[lcore_id], TYPE_REPLAY_RUN, __ATOMIC_RELEASE);
			}
		}
	}

	return 0;
}

/*
 * The main function, which does initialization and calls the per-lcore
 * functions.
 */
int
main(int argc, char *argv[])
{
	/* Initializion the Environment Abstraction Layer (EAL). 8< */
	int ret = rte_eal_init(argc, argv);
	if (ret < 0)
		rte_exit(EXIT_FAILURE, "Error with EAL initialization\n");
	/* >8 End of initialization the Environment Abstraction Layer (EAL). */

	argc -= ret;
	argv += ret;

	/* Check that there is an even number of ports to send/receive on. */
	nb_ports = rte_eth_dev_count_avail();
	
	int arg;
	bool set_mon_id = false;
	bool set_macs = false;
	bool set_ips = false;

	const unsigned char ipdata[10] = "\x86\xdd\x60\x00\x00\x00\x00\x50\xfe\x40";
	rte_memcpy(&ana_headers[12], ipdata, 10);
	const unsigned char padding[10] = "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
	rte_memcpy(&ana_headers[54], padding, 10);
	bool macdst = false;
	bool ipdst = false;
	uint16_t vport, devport;
	int parsed = 0;

	while ((arg = getopt(argc, argv, "n:d:m:i:r:hv")) != -1) {
		switch (arg) {
			case 'n':
				mon_id = strtol(optarg, NULL, 0);
				set_mon_id = true;
				break;
			case 'd':
				// [dpdk virtual port]@[device number as parsed into dpdk]
				sscanf(optarg, "%hu@%hu", &vport, &devport);
				vport_to_devport[vport] = devport;
				devport_to_vport[devport] = vport;
				break;
			case 'm':
				// MAC addresses, source then dest
				if (macdst) {
					parsed = sscanf(optarg, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
									&ana_headers[0], &ana_headers[1], &ana_headers[2],
									&ana_headers[3], &ana_headers[4], &ana_headers[5]);
					set_macs = true;
				}
				else {
					parsed = sscanf(optarg, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
									&ana_headers[6], &ana_headers[7], &ana_headers[8],
									&ana_headers[9], &ana_headers[10], &ana_headers[11]);
					macdst = true;
				}
				if (parsed != 6) {
					rte_exit(EXIT_FAILURE, "Invalid MAC address\n");
				}
				break;
			case 'i':
				// IPv6 addresses, source then dest
				if (ipdst) {
					if (inet_pton(AF_INET6, optarg, &ana_headers[38]) != 1) {
						rte_exit(EXIT_FAILURE, "Invalid IPv6 address\n");
					}
					set_ips = true;
				}
				else {
					if (inet_pton(AF_INET6, optarg, &ana_headers[22]) != 1) {
						rte_exit(EXIT_FAILURE, "Invalid IPv6 address\n");
					}
					ipdst = true;
				}
				break;
			case 'r':
				sscanf(optarg, "%u", &max_replay_size);
				break;
			case 'h':
				printf("Available options:\n");
				printf("  -n    Set monitor ID\n");
				printf("  -d    Set virtual-actual device mappings, as [virtual]@[actual], actual as parsed by dpdk\n");
				printf("  -m    Set MAC addresses for analyzer (source then dest)\n");
				printf("  -i    Set IP addresses for analyzer (source then dest)\n");
				printf("  -r    Set maximum replay size, default %u\n", MIN_REPLAY_SIZE);
				printf("  -h    Print this help\n");
				printf("  -v    Print version\n");
				exit(EXIT_SUCCESS);
			case 'v':
				printf(CREASEVER);
				exit(EXIT_SUCCESS);
			case '?':
				switch (optopt) {
					case 'd':
					case 'm':
					case 'i':
					case 'n':
						rte_exit(EXIT_FAILURE, "Option -%c requires an argument.\n", optopt);
					default:
						rte_exit(EXIT_FAILURE, "Unknown option -%c.\n", optopt);
				}
			default:
				abort();
		}
	}
	if (!set_macs) {
		rte_exit(EXIT_FAILURE, "Missing MAC addresses for analyzer connection.\n");
	}
	if (!set_ips) {
		rte_exit(EXIT_FAILURE, "Missing IP addresses for analyzer connection.\n");
	}
	if (!set_mon_id) {
		rte_exit(EXIT_FAILURE, "Did not set monitor id.\n");
	}
	for (uint16_t i = 0; i < nb_ports; ++i) {
		if (vport_to_devport[i] >= nb_ports) {
			rte_exit(EXIT_FAILURE, "Invalid port mapping for virtual port %hu: %hu beyond %hu.\n", i, vport_to_devport[i], nb_ports);
		}
	}
	if (max_replay_size < MIN_REPLAY_SIZE) max_replay_size = MIN_REPLAY_SIZE;

	printf(CREASEVER);
	printf("Monitor ID: %lu\n", mon_id);
	printf("Virtual port to device port mapping:\n");
	for (uint16_t i = 0; i < nb_ports; ++i) {
		printf("  Virtual port %hu -> Device port %hu\n", i, vport_to_devport[i]);
	}
	printf("Maximum replay size: %u\n", max_replay_size);

	nb_lcores = rte_lcore_count();
	if (nb_lcores <= nb_ports) {
		rte_exit(EXIT_FAILURE, "Not enough cores, have %u, need at least %u\n",
			nb_lcores, nb_ports + 1);
	}
	nb_worker_cores = nb_lcores - nb_ports;
	uint16_t portid;
	unsigned lcore_id = 0, lcore_ctr = 0;
	struct rte_eth_dev_info dev_info;
	struct rte_eth_txconf *txconf;
	uint16_t queueid;
	ssize_t packet_ring_size = 0;


	packet_pool = rte_pktmbuf_pool_create("packet_pool", ((nb_ports - 1)*max_replay_size+256)*BURST_SIZE, RTE_MEMPOOL_CACHE_MAX_SIZE,
		0, PKT_MBUF_DATA_SIZE, rte_socket_id());

	if (packet_pool == NULL)
		rte_exit(EXIT_FAILURE, "Cannot init packet mbuf pool: %s\n", rte_strerror(rte_errno));
	
	for (uint16_t i = 0; i < nb_ports - 1; ++i) {
		packet_rings[i] = NULL;
		char *temp_str = rte_zmalloc("packet_ring_name", 32, RTE_CACHE_LINE_SIZE);
		snprintf(temp_str, 32, "packet_ring_%hu", i);
		struct rte_soring_param prm = {
			.name = temp_str,
			.elems = NUM_MBUFS,
			.elem_size = sizeof(struct rte_mbuf *),
			.meta_size = sizeof(struct packet_metadata),
			.stages = 1,
			.prod_synt = RTE_RING_SYNC_ST,
			.cons_synt = RTE_RING_SYNC_ST
		};
		
		packet_ring_size = rte_soring_get_memsize(&prm);

		if (packet_ring_size < 0)
			rte_exit(EXIT_FAILURE, "Cannot get packet soring size: %s\n", rte_strerror(-packet_ring_size));
		
		packet_rings[i] = rte_zmalloc("packet_ring", packet_ring_size, RTE_CACHE_LINE_SIZE);
		if (packet_rings[i] == NULL)
			rte_exit(EXIT_FAILURE, "Cannot allocate packet soring: %s\n", rte_strerror(rte_errno));

		ret = rte_soring_init(packet_rings[i], &prm);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "Cannot create packet soring: %s\n", rte_strerror(-ret));
	}

	clone_pool = rte_pktmbuf_pool_create("clone_pool", NUM_MBUFS*2, RTE_MEMPOOL_CACHE_MAX_SIZE,
		0, 0, rte_socket_id());

	if (clone_pool == NULL)
		rte_exit(EXIT_FAILURE, "Cannot init clone mbuf pool: %s\n", rte_strerror(rte_errno));

	replay_pool = rte_mempool_create("replay_pool", (nb_ports - 1) * max_replay_size, sizeof(struct replay_buf),
		0, 0, NULL, NULL, NULL, NULL, rte_socket_id(), 0);

	if (replay_pool == NULL)
		rte_exit(EXIT_FAILURE, "Cannot init replay mbuf pool: %s\n", rte_strerror(rte_errno));

	// Each data-port rx lcore records to and replays from its own ring, so the
	// rings can be single-producer single-consumer
	for (uint16_t i = 0; i < nb_ports - 1; ++i) {
		char ring_name[32];
		snprintf(ring_name, 32, "replay_ring_%hu", i);
		replay_rings[i] = rte_ring_create(ring_name, max_replay_size, rte_socket_id(),
			RING_F_SP_ENQ | RING_F_SC_DEQ | RING_F_EXACT_SZ);
		if (replay_rings[i] == NULL)
			rte_exit(EXIT_FAILURE, "Cannot create replay ring: %s\n", rte_strerror(rte_errno));

		replay_run_bufs[i] = rte_malloc("replay_run_bufs", max_replay_size * sizeof(struct replay_buf *), 0);
		if (replay_run_bufs[i] == NULL)
			rte_exit(EXIT_FAILURE, "Cannot allocate replay run buffers: %s\n", rte_strerror(rte_errno));
	}

	/*
	 * Master core handles command handling
	 * ana cores handle sending to analyzer
	 * other cores handle other ports
	 * Master core, for now, solely receives commands and instructs others
	 * Ana core solely handles transmission out of port to analyzer
	 * Other cores receive traffic, add trailer, create clone
	 * they write the clone to a ring the ana cores consume from
	 * Setup must configure ports and then rings.
	 */

	

	/* Initialize ana port */
	lcore_id = rte_get_next_lcore(-1, 0, 0);
	if (lcore_id == RTE_MAX_LCORE)
		rte_exit(EXIT_FAILURE, "Not enough cores\n");
	rx_lcores[0] = lcore_id;
	for (uint16_t vport = 1; vport < nb_ports; ++vport) {
		lcore_id = rte_get_next_lcore(lcore_id, 1, 0);
		if (lcore_id == RTE_MAX_LCORE)
			rte_exit(EXIT_FAILURE, "Not enough cores\n");
		rx_lcores[vport] = lcore_id;
	}
	uint16_t worker_nb_txd = nb_txd;
	// while (worker_nb_txd > nb_txd / nb_worker_cores) {
	// 	worker_nb_txd >>= 1;
	// }
	printf("Using %u worker cores\n", nb_worker_cores);
	printf("Using %u TX descriptors per worker core\n", worker_nb_txd);

	if (1) {
		struct rte_eth_rxconf rxq_conf;
		struct rte_eth_conf local_port_conf = port_conf;
		portid = vport_to_devport[0];

		ret = rte_eth_dev_info_get(portid, &dev_info);
		if (ret != 0)
			rte_exit(EXIT_FAILURE,
				"Error during getting device (port %u) info: %s\n",
				portid, rte_strerror(-ret));

		local_port_conf.rxmode.mtu = RTE_MIN(
			dev_info.max_mtu,
			local_port_conf.rxmode.mtu);

		printf("Initializing port %d on lcore %u... ", portid,
			rx_lcores[0]);
		fflush(stdout);

		ret = rte_eth_dev_configure(portid, 1, nb_worker_cores + 1,
					&local_port_conf);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "Cannot configure device: err=%s, port=%d\n",
				 rte_strerror(-ret), portid);

		ret = rte_eth_dev_adjust_nb_rx_tx_desc(portid, &nb_rxd,
						       &nb_txd);
		if (ret < 0)
			rte_exit(EXIT_FAILURE,
				 "Cannot adjust number of descriptors: err=%s, port=%d\n",
				 rte_strerror(-ret), portid);

		ret = rte_eth_macaddr_get(portid, &ports_eth_addr[portid]);
		if (ret < 0)
			rte_exit(EXIT_FAILURE,
				 "Cannot get MAC address: err=%s, port=%d\n",
				 rte_strerror(-ret), portid);

		print_ethaddr(" Address:", &ports_eth_addr[portid]);
		printf(", ");

		/* init one RX queue */
		queueid = 0;
		printf("rxq=%hu ", queueid);
		fflush(stdout);
		rxq_conf = dev_info.default_rxconf;
		rxq_conf.offloads = local_port_conf.rxmode.offloads;
		ret = rte_eth_rx_queue_setup(portid, queueid, nb_rxd,
					     rte_eth_dev_socket_id(portid),
					     &rxq_conf,
					     packet_pool);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "rte_eth_rx_queue_setup: err=%s, port=%d\n",
				  rte_strerror(-ret), portid);

		lcore_ctr = 0;
		while (lcore_ctr < nb_worker_cores) {
			lcore_id = rte_get_next_lcore(lcore_id, 1, 0);
			if (lcore_id == RTE_MAX_LCORE)
				rte_exit(EXIT_FAILURE, "Not enough cores\n");
			worker_core_ids[lcore_ctr] = lcore_id;
			printf("txq=%u,%hu ", lcore_id, queueid);
			fflush(stdout);

			txconf = &dev_info.default_txconf;
			//printf("txconf offloads: 0x%" PRIx64 "\n", txconf->offloads);
			ret = rte_eth_tx_queue_setup(portid, queueid, worker_nb_txd,
						     rte_lcore_to_socket_id(lcore_id), txconf);
			if (ret < 0)
				rte_exit(EXIT_FAILURE, "rte_eth_tx_queue_setup: err=%s, "
					  "port=%d\n", rte_strerror(-ret), portid);
			queueid++;
			lcore_ctr++;
		}
		nd_txq = queueid;
		printf("txq=%u,%hu (neighbor discovery) ", rte_get_main_lcore(), nd_txq);
		ret = rte_eth_tx_queue_setup(portid, nd_txq, nb_txd,
					     rte_socket_id(), &dev_info.default_txconf);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "rte_eth_tx_queue_setup: err=%s, "
				  "port=%d\n", rte_strerror(-ret), portid);
		ret = rte_eth_dev_start(portid);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "rte_eth_dev_start: err=%d, port=%d\n",
				  ret, portid);

		/* Solicitations go to the address's solicited-node multicast group. */
		struct rte_ether_addr nd_mc = {{0x33, 0x33, 0xff, ana_headers[35],
						ana_headers[36], ana_headers[37]}};
		if (rte_eth_dev_set_mc_addr_list(portid, &nd_mc, 1) != 0 &&
		    rte_eth_allmulticast_enable(portid) != 0)
			printf("warning: port %d receives no neighbor solicitations by multicast ",
			       portid);

		printf("done:\n");
	}

	/* Initializing all ports. 8< */
	for (uint16_t vport = 1; vport < nb_ports; ++vport) {
		struct rte_eth_rxconf rxq_conf;
		struct rte_eth_conf local_port_conf = port_conf;
		portid = vport_to_devport[vport];

		/* limit the frame size to the maximum supported by NIC */
		ret = rte_eth_dev_info_get(portid, &dev_info);
		if (ret != 0)
			rte_exit(EXIT_FAILURE,
				"Error during getting device (port %u) info: %s\n",
				portid, rte_strerror(-ret));

		local_port_conf.rxmode.mtu = RTE_MIN(
		    dev_info.max_mtu,
		    local_port_conf.rxmode.mtu);

		printf("Initializing port %d on lcore %u... ", portid,
			rx_lcores[vport]);
		fflush(stdout);
		ret = rte_eth_dev_configure(portid, 1, nb_worker_cores,
					&local_port_conf);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "Cannot configure device: err=%d, port=%d\n",
					ret, portid);

		ret = rte_eth_dev_adjust_nb_rx_tx_desc(portid, &nb_rxd,
						       &nb_txd);
		if (ret < 0)
			rte_exit(EXIT_FAILURE,
				 "Cannot adjust number of descriptors: err=%d, port=%d\n",
				 ret, portid);

		ret = rte_eth_macaddr_get(portid, &ports_eth_addr[portid]);
		if (ret < 0)
			rte_exit(EXIT_FAILURE,
				 "Cannot get MAC address: err=%d, port=%d\n",
				 ret, portid);

		print_ethaddr(" Address:", &ports_eth_addr[portid]);
		printf(", ");

		/* init one RX queue */
		queueid = 0;
		printf("rxq=%hu ", queueid);
		fflush(stdout);
		rxq_conf = dev_info.default_rxconf;
		rxq_conf.offloads = local_port_conf.rxmode.offloads;
		ret = rte_eth_rx_queue_setup(portid, queueid, nb_rxd,
					     rte_eth_dev_socket_id(portid),
					     &rxq_conf,
					     packet_pool);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "rte_eth_tx_queue_setup: err=%d, port=%d\n",
				  ret, portid);

		/* init one TX queue */
		queueid = 0;
		
		printf("txq=%u,%hu ", rx_lcores[vport], queueid);
		fflush(stdout);

		txconf = &dev_info.default_txconf;
		//printf("txconf offloads: 0x%" PRIx64 "\n", txconf->offloads);
		ret = rte_eth_tx_queue_setup(portid, queueid, nb_txd,
							rte_lcore_to_socket_id(rx_lcores[vport]), txconf);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "rte_eth_tx_queue_setup: err=%s, "
					"port=%d\n", rte_strerror(-ret), portid);

		ret = rte_eth_promiscuous_enable(portid);
		if (ret < 0)
			rte_exit(EXIT_FAILURE,
				"rte_eth_promiscuous_enable: err=%d, port=%d\n",
				ret, portid);
		/* Start device */
		ret = rte_eth_dev_start(portid);
		if (ret < 0)
			rte_exit(EXIT_FAILURE, "rte_eth_dev_start: err=%d, port=%d\n",
				  ret, portid);

		printf("done:\n");
	}
	/* >8 End of initializing all ports. */
	
	tsc_hz = rte_get_tsc_hz();
	printf("Running at %lu hz\n", tsc_hz);

	for (uint16_t vport = 1; vport < nb_ports; ++vport) {
		lcore_id = rx_lcores[vport];
		args[lcore_id].port_id = vport_to_devport[vport];
		args[lcore_id].queue_id = 0;
		rte_eal_remote_launch((lcore_function_t *)crinkle_rx, (void *)&args[lcore_id], lcore_id);
	}
	lcore_ctr = 0;
	while (lcore_ctr < nb_worker_cores) {
		lcore_id = worker_core_ids[lcore_ctr];
		args[lcore_id].port_id = vport_to_devport[0];
		args[lcore_id].queue_id = lcore_ctr;
		rte_eal_remote_launch((lcore_function_t *)crinkle_tx, (void *)&args[lcore_id], lcore_id);
		lcore_ctr++;
	}

	struct rte_mbuf *bufs[BURST_SIZE];
	struct timespec systime;
	struct rte_eth_stats stats;
	uint64_t systime_ns, last_stat_print = 0;
	uint16_t port_id;
	unsigned k;
	int i, nb_rx;
	lcore_id = rx_lcores[0];
	uint64_t last_packets_rx[nb_ports], last_packets_tx[nb_ports];

	signal(SIGINT, signal_handler);
	signal(SIGTERM, signal_handler);

	while (do_run) {
		clock_gettime(CLOCK_REALTIME, &systime);
		systime_ns = timespec64_to_ns(&systime);
		portid = vport_to_devport[0];

		if (systime_ns - last_stat_print > NSEC_PER_SEC) {
			last_stat_print = systime_ns;
			RTE_ETH_FOREACH_DEV(port_id) {
				rte_eth_stats_get(port_id, &stats);
				printf("=== Port %hu stats ===\n", port_id);
				printf("  RX packets: %lu\n", stats.ipackets);
				printf("  RX missed: %lu\n", stats.imissed);
				printf("  RX errors: %lu\n", stats.ierrors);
				printf("  RX no mbuf: %lu\n", stats.rx_nombuf);
				printf("  RX per sec: %lu\n", stats.ipackets - last_packets_rx[port_id]);
				printf("  TX packets: %lu\n", stats.opackets);
				printf("  TX errors: %lu\n", stats.oerrors);
				printf("  TX per sec: %lu\n", stats.opackets - last_packets_tx[port_id]);
				last_packets_rx[port_id] = stats.ipackets;
				last_packets_tx[port_id] = stats.opackets;
			}
		}
		
		nb_rx = rte_eth_rx_burst(portid, 0, bufs, BURST_SIZE);

		if (nb_rx > 0) {
			printf("Received %d command packets on port %hu\n", nb_rx, portid);
		}

		for (i = 0; i < nb_rx; ++i) {
			if (!crinkle_nd_reply(bufs[i], portid))
				crinkle_command_handler(bufs[i], systime_ns);
		}
		rte_pktmbuf_free_bulk(bufs, nb_rx);

		for (k = 1; k < nb_ports; ++k) {
			uint8_t acks = __atomic_load_n(&tx_to_c[rx_lcores[k]], __ATOMIC_ACQUIRE);
			if (acks & TYPE_REPLAY_CLEAR) {
				--c_ctrs[IDX_REPLAY_CLEAR];
				__atomic_fetch_and(&tx_to_c[rx_lcores[k]], (uint8_t)~TYPE_REPLAY_CLEAR, __ATOMIC_RELEASE);
			}
			if (acks & TYPE_REPLAY_RUN) {
				--c_ctrs[IDX_REPLAY_RUN];
				__atomic_fetch_and(&tx_to_c[rx_lcores[k]], (uint8_t)~TYPE_REPLAY_RUN, __ATOMIC_RELEASE);
			}
		}
	}
	RTE_LCORE_FOREACH_WORKER(lcore_id) {
		if (rte_eal_wait_lcore(lcore_id) < 0)
			return -1;
	}

	/* Call lcore_main on the main core only. Called on single lcore. 8< */
	//lcore_main(vport_to_devport, devport_to_vport);
	/* >8 End of called on single lcore. */

	RTE_ETH_FOREACH_DEV(port_id) {
		rte_eth_stats_get(port_id, &stats);
		printf("Port %hu received %lu packets, missed %lu, errors %lu, no buffer %lu\n",
			   port_id, stats.ipackets, stats.imissed, stats.ierrors, stats.rx_nombuf);
	}

	/* clean up the EAL */
	printf("Shutting down...\n");
	rte_eal_cleanup();

	return 0;
}
