
'''sample_R101.py'''

import random
from gavrptw.core import run_gavrptw


def main():
    '''main()'''

    instance_name = 'C101'
    disposal_sites = [10, 50, 15, 55, 82, 97]

    unit_cost = 8.0
    init_cost = 60.0
    wait_cost = 0.5
    delay_cost = 1.5

    run_gavrptw(
        instance_name=instance_name,
        disposal_sites=disposal_sites,
        unit_cost=unit_cost,
        init_cost=init_cost,
        wait_cost=wait_cost,
        delay_cost=delay_cost
    )

if __name__ == '__main__':
    main()
