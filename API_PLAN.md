# API Plan

## 1. Project Overview
This project creates an N x N multiplication table.
The user enters a number N between 1 and 9.

## 2. API Design

### GET /api/health
- Check if the server is running.
- Response: {"status": "ok"}

### POST /api/table
- Generate an N x N multiplication table.
- Input: {"n": 3}
- Output: {"table": [[1,2,3],[2,4,6],[3,6,9]]}

## 3. Error Handling
- N must be an integer between 1 and 9.
- Invalid inputs return an error message.

## 4. Future Improvements
- Add a simple web interface.
- Allow users to save results.
