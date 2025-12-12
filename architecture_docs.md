# Architecture & Rate Limiting Strategy

This document explains the technical implementation of the `value-scanner`'s report fetching system, specifically focusing on how it handles concurrency and strict server rate limits.

## 1. Concurrency Model: The "Workers"

The system uses **asynchronous concurrency** powered by Python's `asyncio`.

- **Orchestrator (`main.py`)**: The main function creates a list of tasks, one for each company in your list.
- **Semaphore**: We use an `asyncio.Semaphore(2)` to limit how many companies are processed *simultaneously*. 
    - Think of the Semaphore as a nightclub bouncer with a clicker. Only 2 companies get into the "VIP Area" (processing) at a time.
    - If efficient, this keeps memory usage low and prevents the script from opening 500 connections at once.

## 2. The "Smart Breather" Strategy

To solve the "exhaustible token bucket" rate limit (where the server lets you make ~20 requests and then blocks you), we implemented a **Batch & Breather** logic.

### How it works:
1.  **Global Counter**: The `HttpReportsFetcher` keeps a count of how many requests have been made across *all* workers.
2.  **The Trigger**: Every time the counter hits a multiple of **10** (e.g., 10, 20, 30...), the system triggers a **"Breather"**.
3.  **The Pause**: The system sleeps for **15 seconds**. This allows the server's invisible "bucket" of allowed tokens to refill.

## 3. Synchronization: The Lock

The critical component that makes the "Breather" work reliably with multiple workers is the `asyncio.Lock()` (`self._breather_lock`).

### The "One Sleeps, All Sleep" Rule
Without the lock, if Worker A triggered the sleep, Worker B would just keep working, using up the server's tokens while A was sleeping. This would defeat the purpose.

**With the Lock:**
1.  **Worker A** hits request #10. It grabs the **Lock** and goes to sleep for 15s.
2.  **Worker B** finishes its current request and tries to start the next one.
3.  **Worker B** tries to grab the Lock to check the counter, but **Worker A is holding it**.
4.  **Worker B** is forced to wait (block) until Worker A wakes up and releases the lock.
5.  **Result**: The entire system strictly pauses. No traffic is sent to the server for 15s.

## 4. Resilience: The "Penalty Box"

If, despite our best efforts, we still trigger a rate limit (HTTP 429 Status):
1.  The fetcher catches the error.
2.  It enters a **"Penalty Box"** mode: it sleeps for **60 seconds**.
3.  This aggressive wait is necessary because getting a 429 usually means the server has put your IP on a temporary blocklist, which takes longer to expire than a normal bucket refill.

## Summary Diagram

```mermaid
graph TD
    A[Start Request] --> B{Acquire Lock}
    B -- Locked --> C[Wait for Breather to End]
    B -- Success --> D{Request Count % 10 == 0?}
    D -- Yes --> E[Hold Lock & Sleep 15s]
    D -- No --> F[Release Lock]
    E --> F
    F --> G[Send HTTP Request]
    G --> H{Result?}
    H -- 200 OK --> I[Save File & Context Switch]
    H -- 429 Blocked --> J[Sleep 60s (Penalty Box) & Retry]
```
