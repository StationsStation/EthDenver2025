# LLM Chat Completion Protocol

## Description

The `llm_chat_completion` protocol defines a structured way to interact with an LLM chat completion API within the Open-AEA framework. It supports creating, retrieving, updating, listing, and deleting chat completions while allowing structured messages and optional keyword arguments.  

### Key Fields  

- **`model`**: A string identifier for the backend model (e.g., `"gpt-4-turbo"`).  
- **`messages`**: A structured list of conversation messages.  
- **`kwargs`**: A flexible mapping for additional API parameters.  

## Specification

```yaml
---
name: llm_chat_completion
author: zarathustra
version: 1.0.0
description: A protocol for openAI LLM chat completion.
license: Apache-2.0
aea_version: '>=1.0.0, <2.0.0'
protocol_specification_id: zarathustra/llm_chat_completion:1.0.0
speech_acts:
  create:
    model: pt:str
    messages: ct:Messages
    kwargs: ct:Kwargs
  retrieve:
    completion_id: pt:str
    kwargs: ct:Kwargs
  update:
    completion_id: pt:str
    kwargs: ct:Kwargs
  list:
    kwargs: ct:Kwargs
  delete:
    completion_id: pt:str
    kwargs: ct:Kwargs
  response:
    data: pt:str
    model_class: pt:str
    model_module: pt:str
  error:
    error_code: ct:ErrorCode
    error_msg: pt:str
...
---
ct:ErrorCode: |
  enum ErrorCodeEnum {
      UNSUPPORTED_PROTOCOL = 0;
      OPENAI_ERROR = 1;
      OTHER_EXCEPTION = 2;
    }
  ErrorCodeEnum error_code = 1;
ct:Messages: |
  message KeyValuePair {
    string key = 1;
    string value = 2;
  }
  message Message {
    repeated KeyValuePair items = 1;
  }
  repeated Message messages = 1;
ct:Kwargs: |
  message Primitive {
    oneof value {
      bool bool_value = 1;
      int64 int_value = 2;
      string float_value = 3;
      string str_value = 4;
      bytes bytes_value = 5;
    }
  }
  message Sequence {
    repeated Primitive values = 1;
  }
  message KeyValuePair {
    string key = 1;
    oneof value {
      Primitive primitive = 2;
      Sequence sequence = 3;
    }
  }
  message Mapping {
    repeated KeyValuePair items = 1;
  }
  message NestedMapping {
    string key = 1;
    oneof value {
      Primitive primitive = 2;
      Sequence sequence = 3;
      Mapping mapping = 4;
    }
  }
  repeated NestedMapping items = 1;
...
---
initiation: [create, retrieve, update, list, delete]
reply:
  create: [response, error]
  retrieve: [response, error]
  update: [response, error]
  list: [response, error]
  delete: [response, error]
  response: []
  error: []
termination: [response, error]
roles: {skill, connection}
end_states: [response, error]
keep_terminal_state_dialogues: true
...
```
