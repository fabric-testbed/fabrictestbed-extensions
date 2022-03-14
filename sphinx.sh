if [ -d "./docs/" ]
then
        sphinx-build -b html docs/source/ docs/build/html
else
        sphinx-quickstart docs
fi
