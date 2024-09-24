# LLM Debugger Zsh Plugin

![LLM Debugger](https://img.shields.io/badge/Zsh-Plugin-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Python Version](https://img.shields.io/badge/Python-3.7%2B-blue)
![OpenAI](https://img.shields.io/badge/OpenAI-API-brightgreen)

**LLM Debugger** is a Zsh plugin that enhances your shell experience by leveraging large language models (LLMs) to debug failed commands. When a command prefixed with `?` fails, the plugin analyzes the error and suggests a corrected command, streamlining your workflow and reducing frustration.

## Video Preview

![Preview](assets/preview.webm)

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Key Bindings](#key-bindings)
- [Logging](#logging)
- [Developer Guide](#developer-guide)
  - [Architecture Overview](#architecture-overview)
  - [Tool Calling Mechanism](#tool-calling-mechanism)
  - [Adding New Tools](#adding-new-tools)
  - [OpenAI Integration](#openai-integration)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Automatic Command Debugging**: Prefix commands with `?` to execute them with enhanced debugging. If the command fails, receive intelligent suggestions to fix the issue.
- **Seamless Integration with OpenAI**: Utilizes OpenAI's GPT models to analyze errors and provide actionable command-line suggestions.
- **Interactive Suggestions**: Accept suggestions with `Tab` or dismiss them with `Escape`.
- **Comprehensive Logging**: Detailed logs are maintained for debugging and monitoring purposes.
- **Customizable Debugging**: Toggle debugging on or off and customize log file locations.

## Prerequisites

Before installing the LLM Debugger Zsh Plugin, ensure you have the following:

- **Zsh Shell**: The plugin is designed for Zsh. Ensure you are using Zsh as your default shell.
- **Python 3.7+**: Required to run the `llm_debugger.py` script.
- **OpenAI API Key**: An API key from OpenAI to access their language models.

## Installation

### 1. Clone the Repository

First, clone the repository to a directory of your choice:
```sh
git clone https://github.com/matbee-eth/zsh-llm-debugger.git ~/.oh-my-zsh/custom/plugins/llm_debugger
```

### 2. Install Dependencies

Ensure you have Python 3.7+ installed. Then, install the required Python packages:

```sh
pip install -r ~/.oh-my-zsh/custom/plugins/llm_debugger/requirements.txt
```

### 3. Enable the Plugin

Add `llm_debugger` to the list of plugins in your `.zshrc`:

```sh
plugins=(
    # ... other plugins
    llm_debugger
)
```

Reload your Zsh configuration:

```sh
source ~/.zshrc
```

## Configuration

### 1. Set Environment Variables

The plugin requires certain environment variables to function correctly:

- **Enable/Disable Debugging**: Control the debugging mode.

  ```sh
  export LLM_DEBUGGER_DEBUG=1  # Set to 1 to enable debugging, 0 to disable
  ```

- **OpenAI API Key**: Set your OpenAI API key.

  ```sh
  export LLM_DEBUGGER_OPENAI_API_KEY="your-openai-api-key"
  ```

Add these to your `.zshrc` or relevant configuration file.

### 2. Python Script Configuration

The plugin relies on the `llm_debugger.py` script. Ensure it's executable and located in the plugin directory:

```sh
chmod +x ~/.oh-my-zsh/custom/plugins/llm_debugger/llm_debugger.py
```

### 3. Optional: Customize Log File Locations

By default, logs are stored in your home directory. You can change this by modifying the `LLM_DEBUGGER_LOG_FILE` and `FIFO_PATH` variables in the `llm_debugger.plugin.zsh` script.

## Usage

### Executing Commands with Debugging

To execute a command with debugging, prefix it with `?`. For example:

```sh
? git sttus
```

If the command fails, the plugin will analyze the error and suggest a corrected command:

```
Analyzing... /
Suggested command: git status
```

### Accepting Suggestions

- **Accept Suggestion**: Press `Tab` to replace the failed command with the suggested one.
- **Cancel Suggestion**: Press `Escape` to dismiss the suggestion and retain the original command.

## Key Bindings

- **Tab (`^I`)**: Accept the suggested command and execute it immediately.
- **Escape (`\e`)**: Cancel the suggestion and keep the original failed command in the terminal.

These bindings are dynamically set when a suggestion is available and restored to their original behavior afterward.

## Logging

The plugin maintains logs for both the Zsh plugin and the Python script:

- **Zsh Plugin Log**: `~/.llm_debugger_zsh.log`
- **Python Script Log**: `~/.llm_debugger.log`

These logs contain debug information, error details, and other relevant data to help you monitor the plugin's activity and troubleshoot issues.

## Developer Guide

### Architecture Overview

The **LLM Debugger Zsh Plugin** consists of two main components:

1. **Zsh Plugin (`llm_debugger.plugin.zsh`)**: Handles user interactions within the Zsh shell, intercepts commands prefixed with `?`, manages key bindings for accepting or canceling suggestions, and communicates with the Python backend for analysis.

2. **Python Script (`llm_debugger.py`)**: Acts as the backend service that interacts with OpenAI's API to analyze failed commands, executes allowed shell functions, and returns suggestions to the Zsh plugin via a FIFO (First-In-First-Out) pipe.

![Architecture Diagram](https://your-diagram-url.com/architecture.png) *(Replace with an actual diagram URL if available)*

### Tool Calling Mechanism

The plugin employs a tool-calling mechanism to execute specific shell functions that assist in analyzing and debugging failed commands. Here's how it works:

1. **Command Execution and Failure Detection**:
   - When a user prefixes a command with `?`, the Zsh plugin executes the command.
   - If the command fails (non-zero exit status), the plugin triggers the debugging process.

2. **Interacting with the Python Backend**:
   - The failed command details are sent to the `llm_debugger.py` script.
   - The Python script gathers comprehensive error details and communicates with the OpenAI API to generate suggestions.

3. **Tool Execution**:
   - The Python script defines a set of allowed functions (tools) such as `list_directory`, `print_working_directory`, `list_processes`, and `display_file_contents`.
   - These tools are invoked by the assistant to gather additional information required for accurate suggestions.
   - The results from these tools are sent back to the assistant to refine the suggestions.

4. **Suggestion Delivery**:
   - The assistant processes the analysis and returns a suggested command.
   - The Zsh plugin receives this suggestion and displays it to the user, allowing for interactive acceptance or cancellation.

### Adding New Tools

To extend the functionality of the LLM Debugger, you can add new tools (functions) that the assistant can utilize. Follow these steps:

1. **Define the Tool in Python**:
   - Open `llm_debugger.py`.
   - Locate the `ALLOWED_FUNCTIONS` dictionary.
   - Add a new entry with the tool's name, description, and parameters.

   ```python
   ALLOWED_FUNCTIONS = {
       # Existing tools...
       "new_tool_name": {
           "name": "new_tool_name",
           "description": "Description of what the new tool does.",
           "parameters": {
               "type": "object",
               "properties": {
                   "param1": {
                       "type": "string",
                       "description": "Description for param1."
                   },
                   # Add more parameters as needed
               },
               "required": ["param1"]  # Specify required parameters
           }
       },
   }
   ```

2. **Implement the Tool Logic**:
   - In the `handle_function_call` function, add a new `elif` block for your tool.

   ```python
   def handle_function_call(function_call):
       # Existing code...
       if function_name == "new_tool_name":
           param1 = arguments.get('param1')
           if not param1:
               return {"error": "Missing 'param1' argument."}
           # Implement the tool's functionality
           command = f"your_command {shlex.quote(param1)}"
           stdout, stderr, exit_status = execute_shell_command(command)
           return {
               "stdout": stdout,
               "stderr": stderr,
               "exit_status": exit_status
           }
       # Existing code...
   ```

3. **Update the Assistant's Tools**:
   - Ensure that the assistant is aware of the new tool by adding it to the `tools` list in the `create_assistant` function.

   ```python
   def create_assistant():
       # Existing code...
       tools=[
           # Existing tools...
           {
               "type": "function",
               "function": {
                   "name": "new_tool_name",
                   "description": "Description of what the new tool does.",
                   "parameters": {
                       "type": "object",
                       "properties": {
                           "param1": {
                               "type": "string",
                               "description": "Description for param1."
                           },
                           # Add more parameters as needed
                       },
                       "required": ["param1"]
                   }
               }
           },
       ],
       # Existing code...
   ```

4. **Restart the Plugin**:
   - After making changes, reload your Zsh configuration to apply the updates.

   ```sh
   source ~/.zshrc
   ```

### OpenAI Integration

The LLM Debugger leverages OpenAI's GPT models to analyze failed commands and generate suggestions. Here's how the integration works:

1. **Assistant Creation**:
   - The Python script initializes an OpenAI assistant named "Shell Debugger" with predefined instructions and tools.
   - The assistant is responsible for analyzing errors and formulating suggestions based on the gathered information.

2. **Event Handling**:
   - The script listens for events from the assistant, such as when a run requires action (e.g., executing a tool) or when a final suggestion is ready.
   - It manages the lifecycle of assistant interactions, ensuring that tool outputs are correctly submitted and suggestions are relayed back to the Zsh plugin.

3. **Security and Rate Limiting**:
   - **API Key Management**: Ensure that your OpenAI API key (`LLM_DEBUGGER_OPENAI_API_KEY`) is kept secure and not exposed in logs or error messages.
   - **Usage Monitoring**: Be aware of OpenAI's rate limits and pricing to manage costs effectively. Monitor your usage to prevent unexpected charges.

4. **Customization**:
   - You can modify the assistant's instructions or tools to better fit your debugging needs.
   - Adjust the verbosity of logs in the Python script to balance between detail and performance.

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please [open an issue](https://github.com/matbee-eth/zsh-llm-debugger/issues). Pull requests are also appreciated.

Before contributing, please ensure that your code adheres to the following guidelines:

- **Code Quality**: Follow best practices for shell scripting and Python programming.
- **Documentation**: Update the README.md and other relevant documentation when adding new features or tools.
- **Testing**: Test your changes thoroughly to prevent regressions.

## License

This project is licensed under the [MIT License](LICENSE).

---

**Disclaimer**: This plugin interacts with OpenAI's API and may incur costs based on usage. Ensure you monitor your API usage and manage your API keys securely.
