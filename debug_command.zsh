#!/bin/zsh

# debug_command.zsh
# Usage: ./debug_command.zsh <command> [args...]

# Function to display usage information
usage() {
    echo "Usage: $0 <command> [args...]"
    echo "Example: $0 ls /nonexistent_directory"
    exit 1
}

# Check if at least one argument is provided
if [ $# -lt 1 ]; then
    usage
fi

# Reconstruct the command from arguments
user_command="$@"

# Log file for the ZSH script
log_file="debug_command.log"

# Start logging
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Starting execution of command: $user_command" | tee -a "$log_file"

# Create temporary files to capture stdout and stderr
temp_stdout=$(mktemp)
temp_stderr=$(mktemp)
temp_json=$(mktemp)

# Function to clean up temporary files on exit
cleanup() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Cleaning up temporary files." | tee -a "$log_file"
    rm -f "$temp_stdout" "$temp_stderr" "$temp_json"
}
trap cleanup EXIT

# Execute the command using ZSH, capturing stdout and stderr
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Executing command..." | tee -a "$log_file"

# Disable 'set -e' behavior temporarily to handle command failure manually
set +e
zsh -c "$user_command" >"$temp_stdout" 2>"$temp_stderr"
exit_status=$?
set -e  # Re-enable 'set -e' if needed later

# Display stdout
if [ -s "$temp_stdout" ]; then
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Command STDOUT:" | tee -a "$log_file"
    cat "$temp_stdout" | tee -a "$log_file"
fi

# Display stderr
if [ -s "$temp_stderr" ]; then
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Command STDERR:" | tee -a "$log_file"
    cat "$temp_stderr" | tee -a "$log_file" >&2
fi

# If the command failed, proceed to interact with the Python shell debugger
if [ $exit_status -ne 0 ]; then
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Command failed with exit status $exit_status. Launching shell debugger..." | tee -a "$log_file"

    # Gather additional error details
    working_directory=$(pwd)
    shell_path="$SHELL"
    PATH_var="$PATH"
    system_information=$(uname -a)

    if [ -f /etc/os-release ]; then
        os_release=$(cat /etc/os-release)
    else
        os_release="OS release information not available"
    fi

    # Extract the base command (first word of the user command)
    base_command=$(echo "$user_command" | awk '{print $1}')

    if command -v "$base_command" >/dev/null 2>&1; then
        command_binary_details=$(which "$base_command")
        command_version=$("$base_command" --version 2>/dev/null || echo "Version information not available")
    else
        command_binary_details="Command not found in PATH"
        command_version="Version information not available"
    fi

    # Gather environment variables as a JSON object using jq
    environment_variables=$(env | jq -Rn '
        [inputs | split("=") | {(.[0]): .[1]}] | add
    ')

    # Properly escape multi-line string fields using jq and remove trailing newlines
    escaped_os_release=$(echo "$os_release" | tr -d '\n' | jq -Rs .)
    escaped_system_information=$(echo "$system_information" | tr -d '\n' | jq -Rs .)
    escaped_command_binary_details=$(echo "$command_binary_details" | tr -d '\n' | jq -Rs .)
    escaped_command_version=$(echo "$command_version" | tr -d '\n' | jq -Rs .)

    # Create a JSON payload with all error details
    error_details=$(jq -n \
        --arg command "$user_command" \
        --arg exit_status "$exit_status" \
        --argjson stdout "$(cat "$temp_stdout" | jq -R . | jq -s .)" \
        --argjson stderr "$(cat "$temp_stderr" | jq -R . | jq -s .)" \
        --arg working_directory "$working_directory" \
        --arg shell "$shell_path" \
        --arg PATH "$PATH_var" \
        --argjson system_information "$escaped_system_information" \
        --argjson os_release "$escaped_os_release" \
        --argjson command_binary_details "$escaped_command_binary_details" \
        --argjson command_version "$escaped_command_version" \
        --argjson environment_variables "$environment_variables" \
        '{
            command: $command,
            exit_status: ($exit_status | tonumber),
            stdout: $stdout,
            stderr: $stderr,
            working_directory: $working_directory,
            shell: $shell,
            PATH: $PATH,
            system_information: $system_information,
            os_release: $os_release,
            command_binary_details: $command_binary_details,
            command_version: $command_version,
            environment_variables: $environment_variables
        }')

    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Error details gathered." | tee -a "$log_file"

    # Optionally, verify the JSON structure
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Generated JSON payload:" | tee -a "$log_file"
    echo "$error_details" | jq . | tee -a "$log_file"

    # Save the JSON payload to a temporary file
    echo "$error_details" > "$temp_json"
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Error details saved to $temp_json." | tee -a "$log_file"

    # Check if Python script exists
    python_script="shell_debugger.py"
    if [ ! -f "$python_script" ]; then
        echo "[$(date +"%Y-%m-%d %H:%M:%S")] Python shell debugger script not found: $python_script" | tee -a "$log_file"
        exit 1
    fi

    # Execute the Python shell debugger script with the JSON file
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Executing Python shell debugger script..." | tee -a "$log_file"
    python3 "$python_script" "$temp_json" | tee -a "$log_file"

    insert_final_response() {
        LBUFFER+="final response from model"
    }
fi
