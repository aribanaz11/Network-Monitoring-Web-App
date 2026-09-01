#!/bin/bash
# ==============================================================================
# NetWatch - Linux Troubleshooting & Process Diagnostics Helper
# Target Skills: Linux, Shell Scripting, Process Management, Log Analysis, TCP/IP
# ==============================================================================
echo "=========================================================="
echo " NetWatch - Linux System & Network Diagnostics Suite"
echo "=========================================================="

echo -e "\n[1] CPU & Memory Utilization (top / free / df):"
free -h || echo "free not available on this platform"
df -h / || echo "df not available"

echo -e "\n[2] Checking NetWatch Process Status (ps / pgrep):"
ps aux | grep -E "manage.py|celery|python" | grep -v grep || echo "No active NetWatch Python processes."

echo -e "\n[3] Network Port Listening Status (ss / netstat):"
ss -tulpn | grep -E "8000|6379|5432|27017|9092" || netstat -tuln 2>/dev/null | grep -E "8000|6379|5432|27017|9092" || echo "Check port tools ss/netstat"

echo -e "\n[4] Recent Application Logs (tail / grep):"
if [ -f "backend/netwatch.log" ]; then
    tail -n 20 backend/netwatch.log
else
    echo "netwatch.log will be created once traffic is received."
fi

echo "=========================================================="
echo " Diagnostic Completed."
echo "=========================================================="
