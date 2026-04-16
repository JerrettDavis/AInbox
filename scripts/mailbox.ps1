#!/usr/bin/env pwsh
# Wrapper script to invoke mailbox CLI on Windows
param([Parameter(ValueFromRemainingArguments=$true)] $Args)

& mailbox @Args
