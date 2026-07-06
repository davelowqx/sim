from decimal import Decimal
import logging
from multiprocessing import Process, Queue, Event
import multiprocessing
multiprocessing.set_start_method('fork')
from typing import Type

from agents import Agent, ExchangeAdapter, MarketMaker, NoiseTrader
from exchange import Exchange, EventBus
from server import run_server

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

def get_sim_processes(to_server_q: Queue) -> list[Process]:
    exchange_q = Queue()
    mm1_q, mm2_q = Queue(), Queue()
    noise_trader_q = Queue()
    mm1_client_id = "MM1"
    mm2_client_id = "MM2"
    noise_trader_client_id = "A"

    processes : list[Process] = []
    processes.append(
        Process(
            target=run_exchange, 
            args=(EventBus(
                send_qs={
                    mm1_client_id: mm1_q,
                    mm2_client_id: mm2_q,
                    noise_trader_client_id: noise_trader_q,
                    "": to_server_q
                },
                rcv_q=exchange_q
            ),)
        )
    )
    processes.append(
        Process(
            target=run_agent, 
            args=(MarketMaker,),
            kwargs={
                "offset": Decimal("0.01"),
                "client_id": mm1_client_id,
                "exchange_adapter": ExchangeAdapter(
                    client_id=mm1_client_id,
                    send_q=exchange_q,
                    rcv_q=mm1_q
                )
            }
        )
    )
    processes.append(
        Process(
            target=run_agent, 
            args=(MarketMaker,),
            kwargs={
                "offset": Decimal("0.02"),
                "client_id": mm2_client_id,
                "exchange_adapter": ExchangeAdapter(
                    client_id=mm2_client_id,
                    send_q=exchange_q,
                    rcv_q=mm2_q
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
                    send_q=exchange_q,
                    rcv_q=noise_trader_q
                )
            }
        )
    )

    return processes

def sim_launcher(start_event: Event, stop_event: Event, to_server_q: Queue):
    sim_procs : list[Process] = []
    while True:
        if not sim_procs:
            start_event.wait()
            sim_procs = get_sim_processes(to_server_q)
            for p in sim_procs:
                p.start()
        else:
            stop_event.wait()
            for p in sim_procs:
                p.terminate()
            for p in sim_procs:
                p.join(timeout=2)
            sim_procs = []

def main():
    start_event, stop_event = Event(), Event()
    to_server_q = Queue()

    server_proc = Process(
        target=run_server,
        args=(start_event, stop_event, to_server_q)
    )
    launcher_proc = Process(
        target=sim_launcher,
        args=(start_event, stop_event, to_server_q)
    )
    server_proc.start()
    launcher_proc.start()

    server_proc.join()
    launcher_proc.join()

if __name__ == "__main__":
    main()