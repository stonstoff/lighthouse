#!/bin/bash

filename=firmware.tar.gz

echo $1";"$filename > latest
echo $1 > firmware/version

cd firmware && tar cvzf ../firmware.tar.gz .
