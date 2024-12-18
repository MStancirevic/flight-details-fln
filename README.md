A function that retrieves a flight schedule of a small operator connecting two points in the North Germany. The flight schedule consists of multiple daily flights between Juist and Norddeich and vice versa.

The function asynchronously retrieves flight details from multiple tasks where each task is all flights found for a single direction in a single day. The output is a table that contains aggregated flight details and is exported to .xlsx

The asynchronous function that uses an event loop takes the following optional arguments:

 - proxy (store your proxy into the .env file and it will be found by loadenv library)
 - n (number of days that will be parsed, starting from today)
 - folder (a subfolder where the output is generated)
 - file (a default file name; when created a date of creation is added to the name)
 - simultaneous (the number of simultaneous tasks used in the semaphore)

Without rotating proxies it has been found that a maximum of 5 simultaneous tasks can be successfully handled with a simple setup.
