"""Prebuilt tools -- ready-to-use tool definitions and handlers.

Two categories:

1. Simple tools (customer-side, single-shot):
   - EndCall: LLM-driven graceful call ending
   - SendDtmf: LLM sends DTMF tones (IVR navigation)
   - WarmTransfer: Transfer to human with hold message

2. Agent tools (server-side sub-agents, multi-turn collection):
   - CollectEmail: Voice-optimized email collection
   - CollectAddress: Mailing address collection
   - CollectPhone: E.164 phone number collection
   - CollectName: First/middle/last name collection
   - CollectDOB: Date of birth collection
   - CollectDigits: PIN/account number collection
   - CollectCreditCard: Secure credit card detail collection

Usage (simple tools)::

    from plivo_agentstack.agent.tools import EndCall, WarmTransfer

    end_call = EndCall()
    transfer = WarmTransfer(destination="+18005551234")

    agent = client.agent.agents.create(
        llm={"tools": [end_call.tool, transfer.tool], ...},
        ...
    )

    @app.on("tool.called")
    def on_tool(session, event):
        if end_call.match(event):
            end_call.handle(session, event)
        elif transfer.match(event):
            transfer.handle(session, event)

Usage (agent tools)::

    from plivo_agentstack.agent.tools import CollectEmail

    collect_email = CollectEmail()

    agent = client.agent.agents.create(
        agent_tools=[collect_email.definition],
        llm={"system_prompt": f"... {collect_email.prompt_hint}", ...},
        ...
    )

    @app.on("agent_tool.completed")
    def on_done(session, event):
        if event.agent_tool_type == "collect_email":
            print(event.result["email_address"])
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Simple tools (customer-side, single-shot)
# ---------------------------------------------------------------------------


class EndCall:
    """Prebuilt: lets the LLM end the call gracefully.

    The LLM decides when the conversation is done and invokes this tool.
    The agent speaks a goodbye message, returns the tool result, then hangs up.

        end_call = EndCall(goodbye_message="Thanks for calling Acme. Goodbye!")
        # Add end_call.tool to agent's tools list
    """

    def __init__(self, goodbye_message: str = "Thank you for calling. Goodbye!"):
        self.goodbye_message = goodbye_message
        self.tool = {
            "name": "end_call",
            "description": (
                "End the call. Use when the conversation is complete, "
                "the user says goodbye, or there is nothing more to discuss."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for ending the call",
                    },
                },
                "required": [],
            },
        }
        self.instructions = (
            "When the conversation is complete or the user wants to end the call, "
            "use the end_call tool. Do not hang up without calling this tool first."
        )

    def match(self, event: Any) -> bool:
        return event.name == "end_call"

    def handle(self, session: Any, event: Any) -> str:
        """Handle end_call -- speaks goodbye and hangs up. Returns the reason."""
        reason = event.arguments.get("reason", "conversation complete")
        session.speak(self.goodbye_message)
        session.send_tool_result(event.id, {"status": "ending", "reason": reason})
        session.hangup()
        return reason


class SendDtmf:
    """Prebuilt: lets the LLM send DTMF digits on the call.

    Useful when the agent needs to navigate IVR menus, enter PINs, or
    interact with automated phone systems.

        send_dtmf = SendDtmf()
        # Add send_dtmf.tool to agent's tools list
    """

    def __init__(self) -> None:
        self.tool = {
            "name": "send_dtmf",
            "description": (
                "Send DTMF digits on the call. Use to navigate IVR menus, "
                "enter PINs, or interact with automated phone systems. "
                "Digits can include 0-9, *, and #."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "digits": {
                        "type": "string",
                        "description": "DTMF digits to send (e.g. '1', '123#', '*9')",
                    },
                },
                "required": ["digits"],
            },
        }
        self.instructions = (
            "You can send DTMF tones using the send_dtmf tool. "
            "When navigating an IVR or phone menu, listen to the options "
            "and send the appropriate digit(s)."
        )

    def match(self, event: Any) -> bool:
        return event.name == "send_dtmf"

    def handle(self, session: Any, event: Any) -> str:
        """Handle send_dtmf -- sends digits and returns them."""
        digits = event.arguments.get("digits", "")
        if not digits:
            session.send_tool_error(event.id, "No digits provided")
            return ""
        session.send_dtmf(digits)
        session.send_tool_result(event.id, {"status": "sent", "digits": digits})
        return digits


class WarmTransfer:
    """Prebuilt: lets the LLM initiate a warm transfer to a human agent.

    The LLM calls the transfer tool with a reason. The handler speaks a
    hold message to the caller, then transfers the call.

        transfer = WarmTransfer(destination="+18005551234")
        # Add transfer.tool to agent's tools list

        @app.on("tool.called")
        def on_tool(session, event):
            if transfer.match(event):
                transfer.handle(session, event)
    """

    def __init__(
        self,
        destination: str | list[str] = "",
        hold_message: str = "Let me connect you with a specialist. One moment please.",
        dial_mode: str = "parallel",
        timeout: int = 30,
        tool_name: str = "transfer_to_human",
    ) -> None:
        self._tool_name = tool_name
        self.destination = destination
        self.hold_message = hold_message
        self.dial_mode = dial_mode
        self.timeout = timeout
        self.tool = {
            "name": tool_name,
            "description": (
                "Transfer the call to a human agent. Use when the user "
                "requests a human, or when you cannot resolve their issue."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for the transfer",
                    },
                },
                "required": ["reason"],
            },
        }
        self.instructions = (
            "If the user asks to speak with a human, a manager, or a real person, "
            "or if you cannot resolve their issue, use the transfer_to_human tool. "
            "Briefly explain why you are transferring before doing so."
        )

    def match(self, event: Any) -> bool:
        return event.name == self._tool_name

    def handle(self, session: Any, event: Any) -> str:
        """Handle transfer -- speaks hold message and initiates transfer."""
        reason = event.arguments.get("reason", "user requested transfer")
        if self.hold_message:
            session.speak(self.hold_message)
        dest = self.destination
        if not dest:
            session.send_tool_error(event.id, "No transfer destination configured")
            return ""
        session.transfer(dest, dial_mode=self.dial_mode, timeout=self.timeout)
        session.send_tool_result(event.id, {"status": "transferring", "reason": reason})
        return reason


# ---------------------------------------------------------------------------
# Agent tools (server-side sub-agents, multi-turn collection)
# ---------------------------------------------------------------------------


class CollectEmail:
    """Agent tool: collect and verify an email address via voice.

    Uses a server-side sub-agent for multi-turn collection with validation.

        collect_email = CollectEmail()
        agent = client.agent.agents.create(
            agent_tools=[collect_email.definition],
            ...
        )

        @app.on("agent_tool.completed")
        def on_done(session, event):
            if event.agent_tool_type == "collect_email":
                print(event.result["email_address"])
    """

    DEFAULT_ON_ENTER = "Ask the user to provide their email address."

    def __init__(
        self,
        *,
        tool_name: str = "collect_email",
        tool_description: str = "Collect an email address from the user.",
        require_confirmation: bool = True,
        on_enter_message: str | None = None,
        instructions: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._config: dict = {
            "tool_name": tool_name,
            "tool_description": tool_description,
            "require_confirmation": require_confirmation,
            "on_enter_message": on_enter_message or self.DEFAULT_ON_ENTER,
            "timeout_s": timeout_s,
        }
        if instructions:
            self._config["instructions"] = instructions

    @property
    def definition(self) -> dict:
        return {"type": "collect_email", "config": self._config}

    @property
    def prompt_hint(self) -> str:
        return f"When you need the user's email, use the {self._config['tool_name']} tool."


class CollectAddress:
    """Agent tool: collect and verify a mailing address via voice.

    Handles international addresses from any country.

        collect_address = CollectAddress()
        agent = client.agent.agents.create(agent_tools=[collect_address.definition], ...)
    """

    DEFAULT_ON_ENTER = "Ask the user to provide their mailing address."

    def __init__(
        self,
        *,
        tool_name: str = "collect_address",
        tool_description: str = "Collect a mailing address from the user.",
        require_confirmation: bool = True,
        on_enter_message: str | None = None,
        instructions: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._config: dict = {
            "tool_name": tool_name,
            "tool_description": tool_description,
            "require_confirmation": require_confirmation,
            "on_enter_message": on_enter_message or self.DEFAULT_ON_ENTER,
            "timeout_s": timeout_s,
        }
        if instructions:
            self._config["instructions"] = instructions

    @property
    def definition(self) -> dict:
        return {"type": "collect_address", "config": self._config}

    @property
    def prompt_hint(self) -> str:
        return (
            f"When you need the user's address, use the {self._config['tool_name']} tool."
        )


class CollectDigits:
    """Agent tool: collect a sequence of digits via DTMF or voice.

    Supports both keypad tones and spoken digits.

        collect_pin = CollectDigits(num_digits=4, label="PIN")
        agent = client.agent.agents.create(agent_tools=[collect_pin.definition], ...)
    """

    DEFAULT_ON_ENTER = "Ask the user to provide the digits."

    def __init__(
        self,
        *,
        num_digits: int = 0,
        label: str = "digits",
        tool_name: str = "collect_digits",
        tool_description: str | None = None,
        require_confirmation: bool = True,
        on_enter_message: str | None = None,
        instructions: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._config: dict = {
            "tool_name": tool_name,
            "tool_description": tool_description or f"Collect {label} from the user.",
            "num_digits": num_digits,
            "label": label,
            "require_confirmation": require_confirmation,
            "on_enter_message": on_enter_message or f"Ask the user to provide their {label}.",
            "timeout_s": timeout_s,
        }
        if instructions:
            self._config["instructions"] = instructions

    @property
    def definition(self) -> dict:
        return {"type": "collect_digits", "config": self._config}

    @property
    def prompt_hint(self) -> str:
        label = self._config.get("label", "digits")
        return (
            f"When you need the user's {label}, use the {self._config['tool_name']} tool."
        )


class CollectPhone:
    """Agent tool: collect and verify a phone number via voice.

    Validates format via regex, strips formatting, reads back in groups.

        collect_phone = CollectPhone()
        agent = client.agent.agents.create(agent_tools=[collect_phone.definition], ...)
    """

    DEFAULT_ON_ENTER = "Ask the user to provide their phone number."

    def __init__(
        self,
        *,
        tool_name: str = "collect_phone",
        tool_description: str = "Collect a phone number from the user.",
        require_confirmation: bool = True,
        on_enter_message: str | None = None,
        extra_instructions: str = "",
        instructions: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._config: dict = {
            "tool_name": tool_name,
            "tool_description": tool_description,
            "require_confirmation": require_confirmation,
            "on_enter_message": on_enter_message or self.DEFAULT_ON_ENTER,
            "timeout_s": timeout_s,
        }
        if extra_instructions:
            self._config["extra_instructions"] = extra_instructions
        if instructions:
            self._config["instructions"] = instructions

    @property
    def definition(self) -> dict:
        return {"type": "collect_phone", "config": self._config}

    @property
    def prompt_hint(self) -> str:
        return (
            f"When you need the user's phone number, "
            f"use the {self._config['tool_name']} tool."
        )


class CollectName:
    """Agent tool: collect and verify a person's name via voice.

    Configurable name parts: first, middle, last. Supports verify_spelling.

        collect_name = CollectName(first_name=True, last_name=True)
        agent = client.agent.agents.create(agent_tools=[collect_name.definition], ...)
    """

    def __init__(
        self,
        *,
        first_name: bool = True,
        last_name: bool = False,
        middle_name: bool = False,
        name_format: str | None = None,
        verify_spelling: bool = False,
        tool_name: str = "collect_name",
        tool_description: str = "Collect the user's name.",
        require_confirmation: bool = True,
        on_enter_message: str | None = None,
        extra_instructions: str = "",
        instructions: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._config: dict = {
            "tool_name": tool_name,
            "tool_description": tool_description,
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "verify_spelling": verify_spelling,
            "require_confirmation": require_confirmation,
            "timeout_s": timeout_s,
        }
        if name_format:
            self._config["name_format"] = name_format
        if on_enter_message:
            self._config["on_enter_message"] = on_enter_message
        if extra_instructions:
            self._config["extra_instructions"] = extra_instructions
        if instructions:
            self._config["instructions"] = instructions

    @property
    def definition(self) -> dict:
        return {"type": "collect_name", "config": self._config}

    @property
    def prompt_hint(self) -> str:
        return f"When you need the user's name, use the {self._config['tool_name']} tool."


class CollectDOB:
    """Agent tool: collect and verify a date of birth via voice.

    Validates the date is real and not in the future. Optionally collects time.

        collect_dob = CollectDOB(include_time=True)
        agent = client.agent.agents.create(agent_tools=[collect_dob.definition], ...)
    """

    def __init__(
        self,
        *,
        include_time: bool = False,
        tool_name: str = "collect_dob",
        tool_description: str = "Collect the user's date of birth.",
        require_confirmation: bool = True,
        on_enter_message: str | None = None,
        extra_instructions: str = "",
        instructions: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._config: dict = {
            "tool_name": tool_name,
            "tool_description": tool_description,
            "include_time": include_time,
            "require_confirmation": require_confirmation,
            "timeout_s": timeout_s,
        }
        if on_enter_message:
            self._config["on_enter_message"] = on_enter_message
        if extra_instructions:
            self._config["extra_instructions"] = extra_instructions
        if instructions:
            self._config["instructions"] = instructions

    @property
    def definition(self) -> dict:
        return {"type": "collect_dob", "config": self._config}

    @property
    def prompt_hint(self) -> str:
        return (
            f"When you need the user's date of birth, "
            f"use the {self._config['tool_name']} tool."
        )


class CollectCreditCard:
    """Agent tool: collect credit card details via voice (security-first).

    Uses sequential sub-tasks: cardholder name, card number, security code,
    expiration date. Supports restart and decline at any point.

        collect_card = CollectCreditCard()
        agent = client.agent.agents.create(agent_tools=[collect_card.definition], ...)
    """

    def __init__(
        self,
        *,
        tool_name: str = "collect_credit_card",
        tool_description: str = "Collect credit card details from the user.",
        require_confirmation: bool = True,
        on_enter_message: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self._config: dict = {
            "tool_name": tool_name,
            "tool_description": tool_description,
            "require_confirmation": require_confirmation,
            "timeout_s": timeout_s,
        }
        if on_enter_message:
            self._config["on_enter_message"] = on_enter_message

    @property
    def definition(self) -> dict:
        return {"type": "collect_credit_card", "config": self._config}

    @property
    def prompt_hint(self) -> str:
        return (
            f"When you need the user's credit card, "
            f"use the {self._config['tool_name']} tool."
        )
