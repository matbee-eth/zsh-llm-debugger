# llm_debugger.plugin.zsh

# Enable debugging (set to 1 to enable, 0 to disable)
export LLM_DEBUGGER_DEBUG=1

# Define paths
plugin_dir="$(cd "$(dirname "${(%):-%x}")" && pwd)"
LLM_DEBUGGER_SCRIPT="${plugin_dir}/openai_debugger.py"
FIFO_PATH="/tmp/llm_debugger_fifo"
LLM_DEBUGGER_LOG_FILE="$HOME/.llm_debugger_zsh.log"  # Log file for Zsh plugin

# Suppress job control messages for job completion
setopt NO_NOTIFY

# Debug function
llm_debugger_debug() {
    if [[ $LLM_DEBUGGER_DEBUG -eq 1 ]]; then
        # Write the debug message to the log file with a timestamp
        print -r -- "$(date '+%Y-%m-%d %H:%M:%S') [DEBUG] $1" >> "$LLM_DEBUGGER_LOG_FILE"
    fi
}

# Function to restore key bindings
llm_debugger_restore_bindings() {
    llm_debugger_debug "Restoring original key bindings"
    bindkey '^I' expand-or-complete
    bindkey '\e' cancel-or-ignore

    # Unbind custom widgets if they exist
    if zle -L | grep -q '^llm_debugger_accept_suggestion$'; then
        zle -D llm_debugger_accept_suggestion 2>/dev/null
        llm_debugger_debug "Unbound llm_debugger_accept_suggestion"
    fi
    if zle -L | grep -q '^llm_debugger_cancel_suggestion$'; then
        zle -D llm_debugger_cancel_suggestion 2>/dev/null
        llm_debugger_debug "Unbound llm_debugger_cancel_suggestion"
    fi
}

# Cleanup function to be called manually if needed
llm_debugger_cleanup() {
    llm_debugger_debug "Running cleanup"
    llm_debugger_restore_bindings

    # Close FIFO if open
    if [[ -n "$LLM_DEBUGGER_FD" && -e /dev/fd/$LLM_DEBUGGER_FD ]]; then
        exec {LLM_DEBUGGER_FD}<&-
        llm_debugger_debug "Closed FIFO FD $LLM_DEBUGGER_FD"
    fi

    # Remove FIFO file if it exists
    if [[ -p $FIFO_PATH ]]; then
        rm -f "$FIFO_PATH"
        llm_debugger_debug "Removed FIFO at $FIFO_PATH"
    fi
}

# Ensure the Python script is executable
if [[ ! -x "$LLM_DEBUGGER_SCRIPT" ]]; then
    llm_debugger_debug "openai_debugger.py not found or not executable at $LLM_DEBUGGER_SCRIPT"
    echo "openai_debugger.py not found or not executable at $LLM_DEBUGGER_SCRIPT"
    return 1
fi

llm_debugger_debug "openai_debugger.py found at $LLM_DEBUGGER_SCRIPT"

# Load the zsh/system module for sysread
if ! zmodload zsh/system 2>/dev/null; then
    llm_debugger_debug "Failed to load zsh/system module"
    echo "Failed to load zsh/system module"
    return 1
fi

llm_debugger_debug "Loaded zsh/system module"

# Global variables to accumulate suggestion data
typeset -g llm_debugger_suggestion=""
typeset -g llm_debugger_has_suggestion=0

# Function to execute command and start analysis if there's an error
llm_debugger_execute_and_analyze() {
    local command="$*"
    llm_debugger_debug "Executing command: $command"

    local exit_status
    local output

    # Execute the command and capture its output and exit status
    output=$(eval "$command" 2>&1)
    exit_status=$?
    llm_debugger_debug "Command exit status: $exit_status"
    llm_debugger_debug "Command output: $output"

    # Print the command output to the user on a new line, retaining colors
    echo
    print -r -- "${(e)output}"

    # If the command failed, start analysis
    if [[ $exit_status -ne 0 ]]; then
        llm_debugger_debug "Command failed, starting analysis"

        # Reset the suggestion variable
        llm_debugger_suggestion=""
        llm_debugger_has_suggestion=0

        # Remove and recreate the FIFO to ensure it's empty
        if [[ -p $FIFO_PATH ]]; then
            rm -f "$FIFO_PATH"
            llm_debugger_debug "Removed existing FIFO at $FIFO_PATH"
        fi
        mkfifo "$FIFO_PATH"
        llm_debugger_debug "Created FIFO at $FIFO_PATH"

        # Open the FIFO for reading and writing to prevent blocking
        exec {LLM_DEBUGGER_FD}<>"$FIFO_PATH"
        llm_debugger_debug "Opened FIFO for read-write with FD $LLM_DEBUGGER_FD"

        # Start the Python script in the background without job control
        "$LLM_DEBUGGER_SCRIPT" "$command" >> "$LLM_DEBUGGER_LOG_FILE" 2>&1 &!
        local python_pid=$!
        llm_debugger_debug "Started openai_debugger.py with PID $python_pid"

        # Display loading state and read suggestion
        llm_debugger_display_loading_and_read_suggestion "$python_pid"
    else
        llm_debugger_debug "Command succeeded, no analysis needed"
    fi
}

# Function to display loading state and read suggestion
llm_debugger_display_loading_and_read_suggestion() {
    local python_pid="$1"
    local spinner=('|' '/' '-' '\\')
    local i=0
    local data=""
    local chunk=""
    local done=0

    # Move to a new line to start the loading indicator
    echo -n ""

    while [[ $done -eq 0 ]]; do
        # Display the loading indicator
        printf "\rAnalyzing... %s" "${spinner[i]}"
        i=$(( (i + 1) % ${#spinner[@]} ))

        # Read from FIFO without blocking
        if sysread -s 1024 -t 0.1 chunk <&$LLM_DEBUGGER_FD; then
            data+="$chunk"
            if [[ $data == *EOF* ]]; then
                llm_debugger_debug "Received EOF, finalizing suggestion"
                # Remove 'EOF' from the data
                data="${data%EOF*}"
                done=1
            fi
        fi

        # Check if Python script has exited unexpectedly
        if ! kill -0 "$python_pid" 2>/dev/null; then
            llm_debugger_debug "openai_debugger.py process $python_pid exited unexpectedly"
            done=1
        fi

        sleep 0.1
    done

    # Clear the loading indicator
    printf "\r%*s\r" "$(tput cols)" ""

    # Define color codes using ANSI escape sequences
    local my_yellow=$'\e[33m'  # Yellow text
    local my_reset=$'\e[0m'    # Reset text attributes

    # Store the suggestion
    llm_debugger_suggestion="${data%$'\n'}"
    llm_debugger_has_suggestion=1
    llm_debugger_debug "Received suggestion: $llm_debugger_suggestion"

    # Display the suggestion on the same line
    local message="${my_yellow}Suggested command:${my_reset} $llm_debugger_suggestion"

    # Print the message
    print -- "$message"

    # Close the file descriptor
    exec {LLM_DEBUGGER_FD}<&-
    llm_debugger_debug "Closed FIFO FD $LLM_DEBUGGER_FD"

    # Bind Tab key to accept the suggestion
    zle -N llm_debugger_accept_suggestion
    bindkey '^I' llm_debugger_accept_suggestion  # '^I' is Tab
    llm_debugger_debug "Bound Tab key to llm_debugger_accept_suggestion"

    # Bind Escape key to cancel the suggestion
    zle -N llm_debugger_cancel_suggestion
    bindkey '\e' llm_debugger_cancel_suggestion  # Escape key
    llm_debugger_debug "Bound Escape key to llm_debugger_cancel_suggestion"
}

# Widget to accept the suggestion when Tab is pressed
llm_debugger_accept_suggestion() {
    llm_debugger_debug "Tab pressed - attempting to accept suggestion"
    if [[ $llm_debugger_has_suggestion -eq 1 ]]; then
        # Replace the command line buffer with the suggestion
        BUFFER="$llm_debugger_suggestion"
        CURSOR=${#BUFFER}
        llm_debugger_debug "Replaced buffer with suggestion: $BUFFER"

        # Unbind the Tab and Escape keys
        # bindkey '^I' expand-or-complete
        # bindkey '\e' cancel-or-ignore
        llm_debugger_debug "Unbound Tab and Escape keys"

        # Remove the custom widgets
        zle -D llm_debugger_accept_suggestion
        zle -D llm_debugger_cancel_suggestion
        llm_debugger_debug "Removed custom widgets"

        # Reset the suggestion variables
        llm_debugger_suggestion=""
        llm_debugger_has_suggestion=0
        llm_debugger_debug "Reset suggestion variables"

        # Refresh the prompt
        zle reset-prompt
    else
        llm_debugger_debug "No suggestion available, performing normal Tab completion"
        zle expand-or-complete
    fi
}

# Widget to cancel the suggestion when Escape is pressed
llm_debugger_cancel_suggestion() {
    llm_debugger_debug "Escape pressed - attempting to cancel suggestion"
    if [[ $llm_debugger_has_suggestion -eq 1 ]]; then
        # Reset the suggestion variables
        llm_debugger_suggestion=""
        llm_debugger_has_suggestion=0
        llm_debugger_debug "Reset suggestion variables"

        # Unbind the Tab and Escape keys
        # bindkey '^I' expand-or-complete
        # bindkey '\e' cancel-or-ignore
        llm_debugger_debug "Unbound Tab and Escape keys"

        # Remove the custom widgets
        zle -D llm_debugger_accept_suggestion
        zle -D llm_debugger_cancel_suggestion
        llm_debugger_debug "Removed custom widgets"

        # Refresh the prompt
        zle reset-prompt
    else
        llm_debugger_debug "No suggestion to cancel, performing normal Escape action"
        zle cancel-line
    fi
}

# Custom accept-line widget to intercept commands starting with '?'
llm_debugger_accept_line() {
    local cmd="${BUFFER}"
    llm_debugger_debug "accept-line widget triggered with buffer: '$cmd'"

    if [[ $cmd == \?* ]]; then
        # Remove the leading '?'
        local command="${cmd#\?}"
        llm_debugger_debug "Intercepted command with '?': $command"

        # Clear the buffer
        BUFFER=""
        zle reset-prompt
        llm_debugger_debug "Cleared buffer and reset prompt"

        # Call the execute and analyze function
        llm_debugger_execute_and_analyze "$command"
    else
        llm_debugger_debug "Command does not start with '?', executing normally"
        zle accept-line-orig
    fi
}

# Save original accept-line as accept-line-orig
zle -A accept-line accept-line-orig
llm_debugger_debug "Saved original accept-line widget as accept-line-orig"

# Replace accept-line with our custom widget
zle -N accept-line llm_debugger_accept_line
llm_debugger_debug "Replaced accept-line with llm_debugger_accept_line"
