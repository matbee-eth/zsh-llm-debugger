#!/usr/bin/env python3
import openai
import logging

import subprocess
import shlex
import json
import os
import sys
from datetime import datetime
import shutil
import time
import fcntl
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
client = OpenAI()

# ==========================
# Configuration and Setup
# ==========================

# Configuration file path
CONFIG_FILE = os.path.expanduser('~/.llm_debugger_config.json')
LOG_FILE = os.path.expanduser('~/.llm_debugger.log')
logging.basicConfig(
    filename=LOG_FILE,
    filemode='w',
    level=logging.DEBUG,  # Change to logging.INFO or logging.ERROR to reduce verbosity
    format='%(asctime)s - %(levelname)s - %(message)s'
)
def load_config():
    """
    Loads the configuration from the CONFIG_FILE.
    If the file does not exist, returns an empty dictionary.
    """
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load config file: {e}", file=sys.stderr)
        return {}

def save_config(config):
    """
    Saves the configuration dictionary to the CONFIG_FILE.
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Failed to save config file: {e}", file=sys.stderr)

# Fetch environment variables
OPENAI_API_KEY = os.getenv('LLM_DEBUGGER_OPENAI_API_KEY', '')

# Validate essential environment variables
if not OPENAI_API_KEY:
    print("Error: LLM_DEBUGGER_OPENAI_API_KEY is not set.", file=sys.stderr)
    sys.exit(1)

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

# ==========================
# Define Allowed Functions
# ==========================

ALLOWED_FUNCTIONS = {
    "list_directory": {
        "name": "list_directory",
        "description": "List files and directories in a specified path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list."
                },
                "options": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["-la", "--help"]
                    },
                    "description": "Options to modify the behavior of the ls command."
                }
            },
            "required": ["path"]
        }
    },
    "print_working_directory": {
        "name": "print_working_directory",
        "description": "Print the current working directory.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    "list_processes": {
        "name": "list_processes",
        "description": "List currently running processes.",
        "parameters": {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["aux", "--help"]
                    },
                    "description": "Options to modify the behavior of the ps command."
                }
            }
        }
    },
    "display_file_contents": {
        "name": "display_file_contents",
        "description": "Display the contents of a specified file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to display."
                }
            },
            "required": ["file_path"]
        }
    }
}

# ==========================
# Helper Functions
# ==========================

def create_assistant():
    """
    Creates an assistant with predefined tools and instructions.
    Returns the assistant ID.
    """
    try:
        assistant = client.beta.assistants.create(
            name="Shell Debugger",
            instructions=(
                "You are a shell debugger. Analyze shell command errors and suggest fixes. "
                "Only suggest the exact shell command to execute in a shell that may solve their problem, no extraneous text."
                "Use the provided functions to gather additional information when necessary."
            ),
            tools=[
                {
                    "type": "function",  # Specify the type of tool as 'function'
                    "function": {
                        "name": "list_directory",
                        "description": "List files and directories in a specified path.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "The directory path to list."
                                },
                                "options": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["-la", "--help"]
                                    },
                                    "description": "Options to modify the behavior of the ls command."
                                }
                            },
                            "required": ["path"]
                        }
                    }
                },
                {
                    "type": "function",  # Specify the type of tool as 'function'
                    "function": {
                        "name": "print_working_directory",
                        "description": "Print the current working directory.",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",  # Specify the type of tool as 'function'
                    "function": {
                        "name": "list_processes",
                        "description": "List currently running processes.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "options": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["aux", "--help"]
                                    },
                                    "description": "Options to modify the behavior of the ps command."
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",  # Specify the type of tool as 'function'
                    "function": {
                        "name": "display_file_contents",
                        "description": "Display the contents of a specified file.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "The path to the file to display."
                                }
                            },
                            "required": ["file_path"]
                        }
                    }
                }
            ],
            model="gpt-4o"  # Specify the model you're using
        )

        logging.debug(f"Assistant created with ID: {assistant.id}")
        return assistant.id
    except Exception as e:
        print(f"Failed to create assistant: {e}", file=sys.stderr)
        sys.exit(1)

def create_thread(error_details):
    """
    Creates a new thread for the conversation.
    Returns the thread ID.
    """
    try:
        thread = thread = client.beta.threads.create(
            messages=[
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": json.dumps(error_details)
                    },
                ],
                }
            ]
        )

        logging.debug(f"Thread created with ID: {thread.id}")
        return thread
    except Exception as e:
        print(f"Failed to create thread: {e}", file=sys.stderr)
        sys.exit(1)

def execute_shell_command(command, env=os.environ):
    """
    Executes a shell command and captures its output and exit status.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            executable='/bin/zsh',  # Ensure using ZSH
            env=env
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return '', str(e), 1

def gather_error_details(command, exit_status, stdout, stderr):
    """
    Gathers detailed error information, including system and environment details.
    """
    details = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "exit_status": exit_status,
        "stdout": stdout,
        "stderr": stderr,
        "working_directory": os.getcwd(),
        "shell": os.getenv('SHELL', ''),
        "PATH": os.getenv('PATH', ''),
        "system_information": subprocess.getoutput('uname -a'),
        "os_release": subprocess.getoutput('cat /etc/os-release') if os.path.exists('/etc/os-release') else "OS release information not available",
        "command_binary_details": subprocess.getoutput(f'which {shlex.split(command)[0]}') if shutil.which(shlex.split(command)[0]) else "Command not found in PATH",
        "command_version": subprocess.getoutput(f'{shlex.split(command)[0]} --version') if shutil.which(shlex.split(command)[0]) else "Version information not available",
        "environment_variables": dict(os.environ)
    }
    return details

def log_error(details):
    """
    Logs the error details to a specified log file.
    """
    log_file = os.path.expanduser('~/.llm_debugger_last_error.log')
    try:
        with open(log_file, 'w') as f:
            json.dump(details, f, indent=4)
    except Exception as e:
        print(f"Failed to write to log file: {e}", file=sys.stderr)

def handle_function_call(function_call):
    """
    Executes the requested function (tool) and returns its output.
    """
    logging.debug(f"function_call details {function_call}")
    function_name = getattr(function_call, 'name', None)
    arguments = json.loads(getattr(function_call, 'arguments', '{}'))

    if function_name not in ALLOWED_FUNCTIONS:
        return {"error": f"Function '{function_name}' is not allowed."}

    # Prepare the command based on the function
    if function_name == "list_directory":
        path = arguments.get('path', '.')
        options = ' '.join(arguments.get('options', []))
        command = f"ls {options} {shlex.quote(path)}"
    elif function_name == "print_working_directory":
        command = "pwd"
    elif function_name == "list_processes":
        options = ' '.join(arguments.get('options', []))
        command = f"ps {options}"
    elif function_name == "display_file_contents":
        file_path = arguments.get('file_path')
        if not file_path:
            return {"error": "Missing 'file_path' argument."}
        command = f"cat {shlex.quote(file_path)}"
    else:
        return {"error": f"Function '{function_name}' is not implemented."}

    stdout, stderr, exit_status = execute_shell_command(command)

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_status": exit_status
    }

def submit_tool_outputs(run, thread_id, tool_outputs):
    """
    Submits the tool outputs back to the assistant to continue the run.
    """
    # Use the submit_tool_outputs_stream helper
    with client.beta.threads.runs.submit_tool_outputs_stream(
        thread_id=thread_id,
        run_id=run.id,
        tool_outputs=tool_outputs,
        event_handler=StreamingEventHandler(),
    ) as stream:
        stream.until_done()

def process_run(run, thread_id):
    """
    Processes a run that requires action (function calls).
    Executes the requested functions and submits their outputs.
    """
    if run.status == "requires_action" and run.required_action.type == "submit_tool_outputs":
        thread_id = thread_id
        tool_calls = run.required_action.submit_tool_outputs.tool_calls

        tool_outputs = []

        for tool_call in tool_calls:
            tool_call_id = tool_call.id
            function_call = tool_call.function

            result = handle_function_call(function_call)

            if 'error' in result:
                print(f"Error executing function {function_call.name}: {result['error']}", file=sys.stderr)
                tool_output = f"Error: {result['error']}"
            else:
                # Combine stdout and stderr
                tool_output = result['stdout'] + result['stderr']

            tool_outputs.append({
                "tool_call_id": tool_call_id,
                "output": tool_output
            })
        # Submit all tool outputs at once
        submit_tool_outputs(run, thread_id, tool_outputs)
    # else:

FIFO_PATH = '/tmp/llm_debugger_fifo'

def create_fifo():
    if not os.path.exists(FIFO_PATH):
        os.mkfifo(FIFO_PATH)

def send_suggestion(suggestion):
    logging.debug(f"send_suggestion: {suggestion}")
    try:
        with open(FIFO_PATH, 'w') as fifo:
            # Strip leading/trailing whitespace and newlines
            suggestion = suggestion.strip()
            fifo.write(suggestion + '\n')
            fifo.write('EOF\n')
            fifo.flush()
    except Exception as e:
        logging.error(f"Failed to write to FIFO: {e}")



def send_command_result(stdout, stderr, exit_status):
    with open(FIFO_PATH, 'w') as fifo:
        fcntl.fcntl(fifo, fcntl.F_SETFL, os.O_NONBLOCK)
        json.dump({
            "type": "command_result",
            "stdout": stdout,
            "stderr": stderr,
            "exit_status": exit_status
        }, fifo)
        fifo.write('\n')
        fifo.flush()
        
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()

    @override
    def on_event(self, event):
        # Handle various events
        logging.debug(f"Event received: {event.event}")
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id  # Retrieve the run ID from the event data
            self.handle_requires_action(event.data, run_id)
        if event.event == 'thread.message.completed':
            self.handle_final_message(event)
        # if event.event == 'thread.message.delta':
        #     self.on_text_delta(event.data.delta, event.data)
        else:
            self.handle_general_event(event)
            
    def on_text_delta(self, delta, data):
        handled = True
        logging.debug(delta)
        # if delta.content[0].type == 'text':
        #     text_value = delta.content[0].text.value
        # logging.debug(f"Text delta received: {text_value}")
        # elif delta.content[0].type == 'command_result':
        #     stdout = delta.command_result.stdout
        #     stderr = delta.command_result.stderr
        #     exit_status = delta.command_result.exit_status
        # logging.debug(f"Command result received: stdout={stdout}, stderr={stderr}, exit_status={exit_status}")

    def handle_requires_action(self, data, run_id):
        tool_outputs = []
        
        for tool in data.required_action.submit_tool_outputs.tool_calls:
            function_call = tool.function
            result = handle_function_call(function_call)
            
            if 'error' in result:
                tool_output = f"Error: {result['error']}"
            else:
                tool_output = result['stdout'] + result['stderr']
            
            tool_outputs.append({
                "tool_call_id": tool.id,
                "output": tool_output
            })
        logging.debug(f"handle_requires_action: {tool_outputs} {run_id}")
        # Submit all tool_outputs at the same time
        self.submit_tool_outputs(tool_outputs, run_id)
 
    def submit_tool_outputs(self, tool_outputs, run_id):
        # Use the submit_tool_outputs_stream helper
        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=StreamingEventHandler(),
        ) as stream:
            stream.until_done()

    def handle_general_event(self, event):
        handled = True
        logging.debug(f"Handling event: {event.event}")
        # Add any specific logic for general events if needed
        
    def handle_final_message(self, event):
        handled = True    
        # Extract the final message content
        # final_message = event.data.content
        # if final_message:
        #     for content_block in final_message:
        #         if content_block.type == 'text':
        #             final_text = content_block.text.value
        # logging.debug(f"Final suggested command: {final_text}")
        
class StreamingEventHandler(EventHandler):
    def __init__(self):
        super().__init__()
        self.suggestion = ""
        try:
            self.fifo = open(FIFO_PATH, 'w')
            fcntl.fcntl(self.fifo, fcntl.F_SETFL, os.O_NONBLOCK)
        except Exception as e:
            logging.error(f"Failed to open FIFO for writing: {e}")
            
    def __del__(self):
        # Close the FIFO
        try:
            self.fifo.close()
        except Exception as e:
            logging.error(f"Failed to close FIFO: {e}")


    @override
    def on_text_created(self, text) -> None:
        self.suggestion += text.value
        # send_suggestion(self.suggestion)

    @override
    def on_text_delta(self, delta, data):
        text_value = delta.value
        self.suggestion += text_value
        logging.debug(f"Text delta received: {text_value}")
        # Write the delta to the FIFO
        try:
            self.fifo.write(text_value)
            self.fifo.flush()
        except Exception as e:
            logging.error(f"Failed to write to FIFO: {e}")

        
    @override
    def handle_general_event(self, event):
        logging.debug(f"Handling event: {event.event}")
        # Add any specific logic for general events if needed
        done = True
    
    @override
    def handle_final_message(self, event):
        logging.debug(f"Final message received: {event}")
        # Send 'EOF' to signal the end
        try:
            self.fifo.write('\nEOF\n')
            self.fifo.flush()
        except Exception as e:
            logging.error(f"Failed to write EOF to FIFO: {e}")
        
        # # Extract the final message content
        # final_message = event.data.content[0]
        # if final_message:
        #     for (type, text) in final_message:
        #         logging.debug(f"content_block:{type}")
        #         if type == 'text':
        #             final_text = text.value
        #             logging.debug(f"Final suggested command: {final_text}")
        #             send_suggestion(final_text)
        #             send_suggestion("EOF")  # Signal EOF to the Zsh script


            
def initiate_run(user_command, assistant_id, thread):
    """
    Initiates a run with the assistant based on the user's command.
    Returns the run object.
    """
    try:
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant_id,
            instructions=(
                "You are a shell debugger. Analyze shell command errors and suggest a working command. "
                "You are to only provide a suggested shell command-line, no other text, and no code blocks. "
                "Use the provided functions to gather additional information when necessary."
            ),
            event_handler=StreamingEventHandler(),
        )  as stream:
            stream.until_done()
    except Exception as e:
        print(f"Failed to initiate run: {e}", file=sys.stderr)
        sys.exit(1)

def monitor_run(run, thread):
    logging.debug(f"DEBUG: Starting to monitor run with ID: {run.id}")
    thread_id = thread.id
    
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run.status == "requires_action":
            process_run(run, thread_id)
        elif run.status == "completed":
            break
        elif run.status in ["failed", "cancelled", "expired"]:
            print(f"Run failed with status: {run.status}", file=sys.stderr)
            break
        time.sleep(1)

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_reply = messages.data[0].content[0].text.value
        logging.debug(f"\nFinal suggestion:{assistant_reply}")

def create_assistant_if_not_exists(config):
    """
    # Creates an assistant if it does not exist in the config.
    Returns the assistant_id.
    """
    assistant_id = config.get('assistant_id')
    if assistant_id:
        return assistant_id
    # Create assistant
    assistant_id = create_assistant()
    # Update config
    config['assistant_id'] = assistant_id
    save_config(config)
    return assistant_id

def create_thread_if_not_exists(config):
    """
    Creates a thread if it does not exist in the config.
    Returns the thread_id.
    """
    # thread_id = config.get('thread_id')
    # if thread_id:
    #     return thread_id
    # Create thread
    thread_id = create_thread()
    # Update config
    config['thread_id'] = thread_id.id
    save_config(config)
    return thread_id

# ==========================
# Main Execution Flow
# ==========================

def main():
    if len(sys.argv) < 2:
        print("Usage: llm_debugger.py <command>", file=sys.stderr)
        sys.exit(1)

    # Load configuration
    config = load_config()

    # Reconstruct the command from arguments
    user_command = ' '.join(sys.argv[1:])

    # Execute the user's command
    stdout, stderr, exit_status = execute_shell_command(user_command)

    # Output the command result to the terminal
    print(stdout, end='')  # stdout may already contain newlines
    if stderr:
        print(stderr, end='', file=sys.stderr)

    # If the command failed, proceed to interact with the assistant
    if exit_status != 0:
        # Create assistant if not exists
        assistant_id = create_assistant_if_not_exists(config)

        # Create thread if not exists
        # Log the error details
        error_details = gather_error_details(user_command, exit_status, stdout, stderr)
        thread = create_thread(error_details)
        
        log_error(error_details)

        # Initiate a run with the assistant
        initiate_run(user_command, assistant_id, thread)
        # Monitor and handle the run
        # monitor_run(run, thread)

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
