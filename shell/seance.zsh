# Séance Shell Zsh integration.

seance_preexec() {
    [[ ${SEANCE_HOOK_RUNNING:-0} == 1 ]] && return 0
    SEANCE_LAST_COMMAND=$1
}

seance_precmd() {
    local __seance_status=$?
    SEANCE_LAST_STATUS=$__seance_status
    if [[ ${SEANCE_HOOK_RUNNING:-0} != 1 && ${SEANCE_ENABLED:-1} != 0 &&
          ${SEANCE_LAST_COMMAND:-} =~ '^[[:space:]]*(/[^[:space:]]*/)?(rm|git|npm|pytest|cargo|make)([[:space:]]|$)' ]]; then
        local SEANCE_HOOK_RUNNING=1
        printf '%s' "$SEANCE_LAST_COMMAND" | command seance hook --status "$__seance_status" 2>/dev/null
    fi
    SEANCE_LAST_COMMAND=
    return "$__seance_status"
}

seance_precmd_restore_status() {
    return "${SEANCE_LAST_STATUS:-0}"
}

if [[ -o interactive && ${SEANCE_SHELL_DISABLED:-0} != 1 ]]; then
    precmd_functions=(${precmd_functions:#seance_precmd})
    precmd_functions=(${precmd_functions:#seance_precmd_restore_status})
    preexec_functions=(${preexec_functions:#seance_preexec})
    preexec_functions=(seance_preexec $preexec_functions)
    precmd_functions=(seance_precmd $precmd_functions seance_precmd_restore_status)
fi
