import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
import pandas as pd
import os
import user_agent_generator
import random
import logging
from dotenv import load_dotenv

load_dotenv()

DEFAULT_PROXY = os.getenv("PROXY")

# Set up logging
logging.basicConfig(
    filename='fln_schedule_errors.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def parse_flight(session, dep, arr, date, semaphore, ua, proxy):
    """ Retrieves flight details for a single date and direction with a semaphore. """
    api = f"https://www.frisonaut.de/de/mobilitaet/faehre/trips?from={dep}&to={arr}&date={date}&types[]=LIGHT_AIRCRAFT&provider[]=30561cf6-84b2-4672-b8d3-e793bdd1bd65&past=true"
    async with semaphore:  # Limit concurrent execution
        try:
            async with session.get(api, ssl=False, proxy=proxy,
                                   headers={"User-Agent": random.choice(ua)}) as response:
                response.raise_for_status()  # Raise HTTP errors
                json_data = await response.json()

                flights = [
                    {
                        "Flight ID": flight_info["id"],
                        "Departure": dep,
                        "Arrival": arr,
                        "Departure Datetime": flight_info["date"],
                        "Arrival Datetime": flight_info["arrivalDate"],
                        "Starting Price": flight_info["startingPrice"],
                        "Additional Price Categories": None if not flight_info["additionalPriceCategories"] else
                        flight_info["additionalPriceCategories"],
                        "Flight Capacity": flight_info["capacity"],
                        "Free Spots": flight_info["capacityMap"]["PERSON"]["free"],
                        "Reserved Spots": flight_info["capacityMap"]["PERSON"]["reserved"],
                        "Car Transportation": flight_info["carTransport"],
                        "Bicycle Transportation": flight_info["bicycleTransport"],
                        "Canceled": flight_info["canceled"],
                        "Delayed": flight_info["delayed"],
                        "Additional": flight_info["additional"]
                    }
                    for flight_info in json_data.get("data", {}).get("trips", [])
                ]
                return flights
        except Exception as e:
            error_message = f"Error fetching flights for {dep} to {arr} on {date}: {e}"
            logging.error(error_message)
            return []  # Return an empty list if there’s an error

async def main(proxy=DEFAULT_PROXY, n=90, folder="output", file="FLN_schedule.xlsx", simultaneous=30, date_format="%Y-%m-%d"):
    """
    This function calls the API to retrieve flight details for the next `n` days,
    starting from today. The function writes the results to an Excel file in a specified folder
    and returns a DataFrame.
    """
    timestamp = datetime.now()
    logging.info(f"Session created at {timestamp}")
    start_time = time.time()

    # Prepare the folder path
    current_dir = os.getcwd()
    output_folder = os.path.join(current_dir, folder)
    os.makedirs(output_folder, exist_ok=True)  # Create the folder if it doesn't exist

    # Prepare date list and directions
    start_date = timestamp.date()
    date_list = [(start_date + timedelta(days=i)).strftime(date_format) for i in range(n)]
    directions = [["NORDDEICH", "JUIST"], ["JUIST", "NORDDEICH"]]
    all_flights = []

    custom_headers = user_agent_generator.generate_unique_uas()
    # Semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(simultaneous)

    async with aiohttp.ClientSession() as session:
        tasks = [
            parse_flight(session, direction[0], direction[1], date, semaphore, custom_headers, proxy)
            for date in date_list for direction in directions
        ]
        try:
            results = await asyncio.gather(*tasks)
            # Flatten the list of lists
            all_flights = [flight for sublist in results for flight in sublist]
        except Exception as e:
            error_message = f"Error during task gathering: {e}"
            logging.error(error_message)

    # Create DataFrame and process datetime columns
    schedule = pd.DataFrame(all_flights)
    if not schedule.empty:
        schedule['Departure Datetime'] = pd.to_datetime(schedule['Departure Datetime'])
        schedule['Departure Date'] = schedule['Departure Datetime'].dt.date
        schedule['Departure Time'] = schedule['Departure Datetime'].dt.time
        schedule['Arrival Datetime'] = pd.to_datetime(schedule['Arrival Datetime'])
        schedule['Arrival Date'] = schedule['Arrival Datetime'].dt.date
        schedule['Arrival Time'] = schedule['Arrival Datetime'].dt.time
        schedule = schedule[['Flight ID', 'Departure', 'Arrival', 'Departure Date', 'Departure Time', 'Arrival Date',
                             'Arrival Time', 'Starting Price', 'Additional Price Categories', 'Flight Capacity',
                             'Free Spots', 'Reserved Spots', 'Car Transportation', 'Bicycle Transportation',
                             'Canceled', 'Delayed', 'Additional']]
        schedule = schedule.sort_values(by=['Departure Date', 'Departure', 'Departure Time'],
                                        ascending=[True, False, True])
        # Write the DataFrame to an Excel file in the specified folder
        output_file = os.path.join(output_folder, f"{datetime.now().strftime(date_format)}_{file}")
        try:
            schedule.to_excel(output_file, index=False)
            logging.info(f"Flight schedule successfully written to {output_file}")
        except Exception as e:
            error_message = f"Error writing to Excel file: {e}"
            logging.error(error_message)
    else:
        logging.warning("No flight data retrieved.")

    logging.info(f"Elapsed time in seconds: {time.time() - start_time}")
    return schedule

# Execution
schedule = asyncio.run(main())
