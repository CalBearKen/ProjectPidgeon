#!/bin/bash
# Script to run all Pidgeon Protocol components for the demo

echo "=== Starting Pidgeon Protocol Components ==="
echo ""
echo "Starting components in the background..."
echo "Press Ctrl+C to stop all components"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping all components..."
    kill $(jobs -p) 2>/dev/null
    wait
    echo "All components stopped."
}

trap cleanup EXIT INT TERM

# Start each component in background
echo "Starting Planner..."
python -m pidgeon.planner &

echo "Starting Interpreter..."
python -m pidgeon.interpreter &

echo "Starting Supervisor..."
python -m pidgeon.supervisor &

echo "Starting Extraction Agent..."
python -m pidgeon.agents --type extraction --id extraction-001 &

echo "Starting Summarization Agent..."
python -m pidgeon.agents --type summarization --id summarization-001 &

echo "Starting Analysis Agent..."
python -m pidgeon.agents --type analysis --id analysis-001 &

echo ""
echo "All components started! Waiting 3 seconds for initialization..."
sleep 3

echo ""
echo "Submitting demo request..."
python examples/document_pipeline/run_demo.py

echo ""
echo "Demo request submitted. Components will continue processing."
echo "Press Ctrl+C to stop all services."
echo ""

# Wait for user interrupt
wait


