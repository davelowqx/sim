import logging
from multiprocessing import Process, Queue
from typing import Type

from agents import Agent, ExchangeAdapter, MarketMaker, NoiseTrader
from exchange import Exchange, EventBus

def run_agent(agent: Type[Agent], **kwargs):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    a = agent(**kwargs)
    a.run()

def run_exchange(event_bus: EventBus):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    exchange = Exchange(event_bus)
    exchange.run()

def main():
    exchange_queue = Queue()
    market_maker_queue = Queue()
    noise_trader_queue = Queue()
    market_maker_client_id = "MARKET_MAKER_1"
    noise_trader_client_id = "NOISE_TRADER"
    
    processes : list[Process] = []
    processes.append(
        Process(
            target=run_exchange, 
            args=(EventBus(
                send_qs={
                    market_maker_client_id: market_maker_queue,
                    noise_trader_client_id: noise_trader_queue
                },
                rcv_q=exchange_queue
            ),)
        )
    )
    processes.append(
        Process(
            target=run_agent, 
            args=(MarketMaker,),
            kwargs={
                "client_id": market_maker_client_id,
                "exchange_adapter": ExchangeAdapter(
                    client_id=market_maker_client_id,
                    send_q=exchange_queue,
                    rcv_q=market_maker_queue
                )
            }
        )
    )
    processes.append(
        Process(
            target=run_agent, 
            args=(NoiseTrader,),
            kwargs={
                "client_id": noise_trader_client_id,
                "exchange_adapter": ExchangeAdapter(
                    client_id=noise_trader_client_id,
                    send_q=exchange_queue,
                    rcv_q=noise_trader_queue
                )
            }
        )
    )

    for p in processes:
        p.start()

    for p in processes:
        p.join()

if __name__ == "__main__":
    main()