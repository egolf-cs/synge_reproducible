# synge_reproducible
A repository capable of reproducing the results of the paper "Synthesis of Distributed Protocols by Enumeration Modulo Isomorphisms."
This code is still in development and it is not intended to be used for purposes other than reproducing the results of the paper.
If a production build is made available a link will be added here.

This README assumes familiarity with the paper. 
In particular, we will reference Tables 1-6 of the paper and the results of Section 5 (Implementation and Evaluation) more generally.

arXiv version of the paper: **link**

## Dependencies

* Python 3.7.12
* networkx, version 2.5.1 (https://pypi.org/project/networkx/)
* ply, version 3.10 (https://pypi.org/project/ply/)

## Usage

From the top-level directory, run 
`backend/distributed_protocol_synthesis/tool.py entry [-h] [-seed SEED] <table_num> <case_study> <states> <algorithm>`

positional arguments:
  table_num   A number 1-6 corresponding to a table from the paper.
  case_study  2PC | ABP
  states      A string of digits corresponding to the states in the A column
              of the table. E.g. if case_study=ABP, then states=12
              correspondes to the row with header ABP;{s1,s2}
  algorithm   unopt | dead | naive | perm

optional arguments:
  -h, --help  show this help message and exit
  -seed SEED  This is specified if and only if the table number is 2 or 5.
              seed must be a value in 0..9. The entry reported in the table is
              an average of the times returned using all 10 of these seeds.