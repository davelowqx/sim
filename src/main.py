import logging
from multiprocessing import Process
from typing import Type

from agents import Agent, MarketMaker, NoiseTrader
from commons import MQClient
from exchange import Exchange

def run_agent(agent: Type[Agent], **kwargs):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    a = agent(**kwargs)
    a.run()

def run_exchange(mq_client: MQClient):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    exchange = Exchange(mq_client)
    exchange.run()

def main():
    processes : list[Process] = []
    processes.append(
        Process(
            target=run_exchange, 
            args=(mq_client)
        )
    )
    processes.append(
        Process(
            target=run_agent, 
            args=(MarketMaker,),
            kwargs={}
        )
    )
    processes.append(
        Process(
            target=run_agent, 
            args=(NoiseTrader,),
            kwargs={}
        )
    )

    for p in processes:
        p.start()

    for p in processes:
        p.join()

if __name__ == "__main__":
    main()