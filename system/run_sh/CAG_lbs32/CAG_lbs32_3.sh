
"""local batch size"""
python main.py -data Cifar10 -gr 200 -algo FedTest -nc 50 -ls 5 -car 100 -calr 25 -mmt 0.9 -ss 30 -gam 0.5 -lbs 32
python main.py -data Cifar10 -gr 200 -algo FedTest -nc 50 -ls 5 -car 100 -calr 25 -mmt 0.7 -ss 30 -gam 0.5 -lbs 32
python main.py -data Cifar10 -gr 200 -algo FedTest -nc 50 -ls 5 -car 100 -calr 25 -mmt 0.3 -ss 30 -gam 0.5 -lbs 32
python main.py -data Cifar10 -gr 200 -algo FedTest -nc 50 -ls 5 -car 100 -calr 25 -mmt 0.1 -ss 30 -gam 0.5 -lbs 3