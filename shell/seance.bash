# Séance Shell Bash integration.

seance_prompt_hook() {
    local __seance_status=$?
    SEANCE_LAST_STATUS=$__seance_status
    if [[ $- == *i* && ${SEANCE_HOOK_RUNNING:-0} != 1 && ${SEANCE_ENABLED:-1} != 0 ]]; then
        local __seance_entry __seance_command
        __seance_entry=$(fc -ln -1 2>/dev/null)
        __seance_command=$__seance_entry
        if [[ $__seance_command =~ ^[[:space:]]*(/[^[:space:]]*/)?(rm|git|npm|pytest|cargo|make)([[:space:]]|$) ]]; then
            local SEANCE_HOOK_RUNNING=1
            printf '%s' "$__seance_command" | command seance hook --status "$__seance_status" 2>/dev/null
        fi
    fi
    return "$__seance_status"
}

seance_prompt_restore_status() {
    return "${SEANCE_LAST_STATUS:-0}"
}

seance_install_prompt_hooks() {
    if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == "declare -a"* ]]; then
        local -a __seance_prompt_entries=()
        local __seance_entry
        for __seance_entry in "${PROMPT_COMMAND[@]}"; do
            [[ $__seance_entry == seance_prompt_hook || $__seance_entry == seance_prompt_restore_status ]] && continue
            __seance_prompt_entries+=("$__seance_entry")
        done
        PROMPT_COMMAND=(seance_prompt_hook "${__seance_prompt_entries[@]}" seance_prompt_restore_status)
    else
        case ";${PROMPT_COMMAND-};" in
            *";seance_prompt_hook;"*) ;;
            *)
                PROMPT_COMMAND="seance_prompt_hook${PROMPT_COMMAND:+; ${PROMPT_COMMAND}}; seance_prompt_restore_status"
                ;;
        esac
    fi
}

if [[ $- == *i* && ${SEANCE_SHELL_DISABLED:-0} != 1 ]]; then
    seance_install_prompt_hooks
fi
unset -f seance_install_prompt_hooks
