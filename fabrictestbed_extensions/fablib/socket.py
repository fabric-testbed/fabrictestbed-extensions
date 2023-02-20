#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Brandon Rice (brandon@retroengineer.com)

import os

class SocketConstants():
    NEXT_LOCAL_PORT = 24253
    NEXT_REMOTE_PORT = 47223

SocketConstants.NEXT_LOCAL_PORT

class SocketHandler:
    def __init__(self, sock, buffer_size=4096):
        self.sock = sock
        self.BUFFER_SIZE = buffer_size

    def __str__(self):
        return f"Socket from {self.sock.getsockname()[0]}:{self.sock.getsockname()[1]} to {self.sock.getpeername()[0]}:{self.sock.getpeername()[1]}."

    def __del__(self): 
        try:
            self.sock.close()

        except Exception as e:
            try:
                ip = self.sock.getsockname()[0]
                port = self.sock.getsockname()[1]
                remote_ip = self.sock.getpeername()[0]
                remote_port = self.sock.getpeername()[1]
                raise RuntimeError(f"Could not close the socket {ip}:{port} connected to {remote_ip}:{remote_port}. These ports may remain open!") from e
            except:
                raise
    
    def _recv_to_newline(self):
        buf = []
        while True:
            data = self.sock.recv(1)
            if not len(data):
                # socket closed
                return None

            if data == b"\n":
                return b"".join(buf)
            buf.append(data)


    def receive(self, output_file='received_data.txt', append=False, quiet=False, newlines=True):
        filename = output_file
        write = True
        if output_file is None:
            # Just print if quiet=False
            write = False
        try:
            if not quiet:
                print('RECEIVED DATA BELOW:')
            if write:
                if append:
                    with open(filename, "ab") as out:
                        while True:
                            bytes_read = self.sock.recv(self.BUFFER_SIZE)
                            if not bytes_read:
                                # Transmitting is done
                                break
                            if not quiet:
                                #if bytes_read != b'':
                                if newlines:
                                    print(f'{bytes_read.decode()}')
                                else:
                                    print(f'{bytes_read.decode()}', end='')
                            out.write(bytes_read)
                            if newlines:
                                out.write(b'\n')
                else:
                    with open(filename, "wb") as out:
                        while True:
                            bytes_read = self.sock.recv(self.BUFFER_SIZE)
                            if not bytes_read:
                                # Transmitting is done
                                break
                            if not quiet:
                                #if bytes_read != b'':
                                if newlines:
                                    print(f'{bytes_read.decode()}')
                                else:
                                    print(f'{bytes_read.decode()}', end='')
                            out.write(bytes_read)
                            if newlines:
                                out.write(b'\n')
            else: ## write == False
                while True:
                    bytes_read = self.sock.recv(self.BUFFER_SIZE)
                    if not bytes_read:
                        # Transmitting is done
                        break
                    if not quiet:
                        #if bytes_read != b'':
                        if newlines:
                            print(f'{bytes_read.decode()}')
                        else:
                            print(f'{bytes_read.decode()}', end='')
        
        except KeyboardInterrupt:
            if not quiet:
                print('\nQUITTING.')
            pass

        except Exception as e:
            raise RuntimeError(f"Error in receiving data using socket.") from e

        finally:
            if not quiet:
                print('\nEND OF RECEIVING.')
                                
                                
    def receive_file(self, output_file=None, append=False, quiet=False):
        filename = self._recv_to_newline().decode("utf-8")
        if not quiet:
            print(f'Receiving: {filename}')
        # Convert Windows file path slash to UNIX style
        filename = filename.replace('\\', '/')
        # remove absolute path if necessary
        filename = os.path.basename(filename)
        if output_file is not None:
            ## Use custom file name as specified: output_file
            filename = output_file
        
        try:
            if append:
                with open(filename, "ab") as file:
                    while True:
                        bytes_read = self.sock.recv(self.BUFFER_SIZE)
                        if not bytes_read:
                            # file transmitting is done
                            break
                        file.write(bytes_read)
            else:
                with open(filename, "wb") as file:
                    while True:
                        bytes_read = self.sock.recv(self.BUFFER_SIZE)
                        if not bytes_read:
                            # file transmitting is done
                            break
                        file.write(bytes_read)

        except KeyboardInterrupt:
            if not quiet:
                print('\nQUITTING.')
            pass

        except Exception as e:
            raise RuntimeError(f"Error in receiving file using socket.") from e

        finally:
            if not quiet:
                print(f'\nFINISHED RECEIVING AND WRITING TO {filename}.')
                
                
    def send(self, data, quiet=False):
        if not quiet:
            print(f'Sending: {data}')

        try:
            self.sock.sendall(data.encode('utf-8'))
            self.sock.sendall(b'\n')
            print('Done sending.')
            
        except KeyboardInterrupt:
            if not quiet:
                print('Quitting.')
            pass

        except Exception as e:
            raise RuntimeError(f"Error in sending file using socket.") from e
            
    def send_file(self, file, quiet=False):
        filename = file
        if not quiet:
            print(f'Sending: {filename}')
            
        try:
            self.sock.sendall(filename.encode('utf-8'))
            self.sock.sendall(b'\n')
            with open(filename, 'rb') as file:
                while True:
                    bytes_read = file.read(self.BUFFER_SIZE)
                    if not bytes_read:
                        # file transmitting is done
                        if not quiet:
                            print('Done sending.')
                        break
                    self.sock.sendall(bytes_read)
            

        except KeyboardInterrupt:
            if not quiet:
                print('Quitting.')
            pass

        except Exception as e:
            raise RuntimeError(f"Error in sending file using socket.") from e