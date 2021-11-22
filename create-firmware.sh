#!/bin/bash

filename=firmware.tar.gz

echo $1 > firmware/version
echo $1";"$filename > latest

cd firmware && tar cvzf ../firmware.tar.gz .
