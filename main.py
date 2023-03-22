from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import sqlite3

app = FastAPI()

# Define the Device model
class Device(BaseModel):
    id: int
    network_address: str
    network_number: int

# Connect to the SQLite database
conn = sqlite3.connect('devices.db')
c = conn.cursor()

# Create the devices table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS devices
             (id INTEGER PRIMARY KEY, network_address TEXT, network_number INTEGER, unique(network_address, network_number)) ''')
conn.commit()

@app.post("/devices/")
async def create_device(device: Device):
    # Add a new device to the database
    try:
        c.execute("INSERT INTO devices (id, network_address, network_number) VALUES (?, ?, ?)", 
                  (device.id, device.network_address, device.network_number))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Device with this ID or Network Number and Network Address combination already exists")
    
    # Create a new BACnet device with the specified ID and network address
    return {"status": "ok"}

@app.get("/devices/")
async def read_devices():
    # Get a list of all devices from the database
    c.execute("SELECT * FROM devices")
    devices = [Device(id=row[0], network_address=row[1], network_number=row[2]) for row in c.fetchall()]
    return devices

@app.get("/devices/{device_id}")
async def read_device(device_id: int):
    # Get a device with the specified ID from the database
    c.execute("SELECT * FROM devices WHERE id=?", (device_id,))
    row = c.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    device = Device(id=row[0], network_address=row[1], network_number=row[2])
    return device

@app.put("/devices/{device_id}")
async def update_device(device_id: int, device: Device):
    # Update the network address and network number of an existing device with the specified ID
    try:
        c.execute("UPDATE devices SET network_address=?, network_number=? WHERE id=?", 
                  (device.network_address, device.network_number, device_id))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Device with this network address already exists")
    
    return {"status": "ok"}

@app.delete("/devices/{device_id}")
async def delete_device(device_id: int):
    # Delete an existing device with the specified ID
    c.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    
    return {"status": "ok"}

@app.get("/networks/")
async def read_networks():
    # Get a list of all unique network numbers from the devices table
    c.execute("SELECT DISTINCT network_number FROM devices")
    networks = [row[0] for row in c.fetchall()]
    return networks

@app.get("/networks/{network_number}")
async def read_devices_on_network(network_number: int):
    # Get a list of all devices on the specified network
    c.execute("SELECT * FROM devices WHERE network_number=?", (network_number,))
    devices = [Device(id=row[0], network_address=row[1], network_number=row[2]) for row in c.fetchall()]

@app.get("/networks/{network_number}/next-address")
async def read_next_address_on_network(network_number: int):
    # Get the next available network address on the specified network
    c.execute("SELECT network_address FROM devices WHERE network_number=? ORDER BY network_address DESC LIMIT 1", (network_number,))
    row = c.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No devices on this network")
    try:
        return {"network_address": int(row[0]) + 1}
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid network address")
