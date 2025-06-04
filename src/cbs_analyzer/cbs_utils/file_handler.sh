#!/usr/bin/env bash


function help_page(){
    cat <<EOF
Chase Bank Statement Processor - Help Guide
=========================================

This script processes Chase Bank PDF statements to extract transaction data.

USAGE:
    ./file_handler.sh [FLAG] [OPTIONS]

FLAGS:
    --get-files             Retrieve PDF files (bank-statements) from a directory
    --grep-files            Search and display content from bank statements
    --checking-summary      Retrieve the checking summary of a given bank statement
    --help                  Display the help page

OPTIONS:
    For --get-files:
        -f <path>     Path to directory containing PDF files (required)
        -e            Echo the list of found PDF files
        -h            Display the help page

    For --grep-files:
        -f <path>     Path to PDF file or directory (required)
        -p <pattern>  Custom regex pattern to search (default: MM/DD date pattern)
        -h            Display the help page
    
    For --checking-summary:
        -f <path>     Path to PDF file or directory (required)
        -h            Display the help page

EXAMPLES:
    1. List all PDFs in a directory:
        ./file_handler.sh --get-files -f "/path/to/statements" -e

    2. Search transactions in a specific PDF:
        ./file_handler.sh --grep-files -f "/path/to/statement.pdf"

    3. Search with custom pattern:
        ./file_handler.sh --grep-files -f "/path/to/statements" -p "YourRegexPattern"
    4. Get checking summary from a PDF:
        ./file_handler.sh --checking-summary -f "/path/to/statement.pdf"
    5. Display help:
        ./file_handler.sh --help

DEPENDENCIES:
    - pdfgrep (for text extraction from PDFs)
    - pip3 and pandas (for data processing)

ERROR HANDLING:
    - Missing required paths will terminate the script
    - Invalid options will show usage instructions
    - Ensure all dependencies are installed before running the script
    - Use Ctrl+C to terminate the script gracefully
    - Ensure you have at least Bash version 4.0
    - Ensure the provided path contains valid PDF files
EOF
exit 0
}
function terminator(){ trap 'echo -e "\nTerminating script..."; cleanup_and_exit' SIGINT ;}
function cleanup_and_exit(){ jobs -p | xargs kill -9 2>/dev/null; exit 1 ;}
function export_kv(){ export "$(tr '[:lower:]' '[:upper:]' <<< "${1}_BIN")"="$2" ;}


function bashVersion(){
    local -i r_major=4 r_minor=0 r_remainder=0
    local -i b_major b_minor b_remainder
    local IFS b_bash r_bash

    IFS=' ' read -r b_major b_minor b_remainder _ <<< "${BASH_VERSINFO[@]}"
    b_bash="${b_major}.${b_minor}.${b_remainder}"
    
    if ((b_major < r_major)) || { (( b_major == r_major )) && (( b_minor < r_minor )); }; then
        r_bash="${r_major}.${r_minor}.${r_remainder}"
        echo "This script requires at least Bash $r_bash. You have $b_bash" >&2
        exit 1
    fi
    
    export CURRENT_BASH_VERSION="$b_bash"
}



function runDependencies(){
    bashVersion
    check_packages "pip3" "pdfgrep"
    check_pip "pandas"
}


function exitFunc(){
    local msg="$1"
    local terminate="${2:-true}"

    if [[ "$terminate" == true ]]; then
        echo "$msg" >&2
        exit 1
    else
        return 1
    fi
}


function checkDir(){
    local fp=""
    local is_dir=true
    local terminate=true
    local msg
    local opt

    OPTIND=1
    while getopts ':f:DTh' opt;
    do
        case $opt in
            f) fp="$OPTARG" ;;
            D) is_dir=false ;;
            T) terminate=false ;;
            h) help_page ;;
            *)
                echo -e "Invalid argument: ${OPTARG}\nUsage: [f (file-path) | D (not-directory) | T (no-terminate) | h (help)]" >&2
                exit 1
                ;;
        esac
    done

    function ef(){ exitFunc "$1" "$terminate" ;}

    if [[ "$is_dir" == true ]]; then
        [[ -z "$fp" ]] \
            && ef "A folder path containing all Chase-Bank statement PDF files is required."
        [[ ! -d "$fp" ]] \
            && ef "The provided path is not a valid directory ('$fp')."
    else
        [[ ! -f "$fp" ]] \
            && ef "The provided path is not a valid file ('$fp')."

        [[ ! -r "$fp" ]] \
            && ef "The provided file is not readable ('$fp')."
    fi
    
}


function check_array(){
    local array=("$@")

    if [[ "${#array[@]}" -eq 0 ]]; then
        echo "No package was provided." >&2
        exit 1
    fi
}



function check_packages(){
    local homebrew_dir="/opt/homebrew/bin"
    local pkgs=("$@")
    local pkg_bin=""

    check_array "${#pkgs[@]}"

    for pkg in "${pkgs[@]}";
    do
        local bin_pkg
        local homebrew_pkg="${homebrew_dir}/${pkg}"

        bin_pkg=$(command -v "$pkg" 2>/dev/null)
        if [[ ! $bin_pkg  && ! -x "$homebrew_pkg" ]]; then
            echo "('$pkg') is not installed. Please install it first." >&2
            exit 1
        fi

        if [[ -n $bin_pkg ]]; then
            pkg_bin=$bin_pkg
        elif [[ -x "$homebrew_pkg" ]]; then
            pkg_bin="$homebrew_pkg"
        fi
        export_kv "$pkg" "$pkg_bin"
    done
}


function check_pip(){
    local pip_pkgs=("$@")

    check_array "${#pip_pkgs[@]}"
    
    function err_msg(){ echo "$1 is not installed. Please install it first." >&2 ;}

    if ! "$PIP3_BIN" >/dev/null 2>&1; then
        err_msg "pip3"
        exit 1
    fi

    for py_pkg in "${pip_pkgs[@]}"; do
        if ! "$PIP3_BIN" show "$py_pkg" >/dev/null 2>&1; then
            err_msg "$py_pkg"
            exit 1
        fi
    done
}



function dirHandler(){
    local fp="$1"
    local seperator="^^"
    local pdf_file
    declare -ga CBS_PDF_FILES

    checkDir -f "$fp"
    
    while IFS= read -r -d $'\0' pdf_file; do
        CBS_PDF_FILES+=("${pdf_file}${seperator}")
    done < <(find "$fp/" -type f -iname "*.pdf" ! -path "$fp" -print0)

    [[ "${#CBS_PDF_FILES[@]}" -eq 0 ]] && {
        echo "The provided path currently does not contain any PDF files. Please check the contents for ('$fp')" >&2
        exit 1
    }
}


function rgrepPDF(){
    local fp=""
    local pattern="[0-1]?[0-9]/[0-3]?[0-9]"
    local opt

    OPTIND=1
    while getopts ':f:p:h' opt;
    do
        case $opt in
            f) fp="$OPTARG" ;;
            p) pattern="$OPTARG" ;;
            h) help_page ;;
            *)
                echo -e "Invalid argument: ${OPTARG}\nUsage: [f (file-path) | p (regex-pattern)]" >&2
                exit 1
                ;;
        esac
    done

    local grep_args=("-e" "$pattern" "$fp")

    if [[ -f "$fp" ]]; then
        checkDir -f "$fp" -D
        "$PDFGREP_BIN" "${grep_args[@]}"
    else
        checkDir -f "$fp"
        grep_args+=("-r")
        "$PDFGREP_BIN" "${grep_args[@]}"
    fi
}


checkingSummary(){
    local fp=""
    local get_keys=false
    local CHECKING_SUMMARY_KEYS=(
        "Beginning Balance"
        "Deposits and Additions"
        "ATM & Debit Card Withdrawals"
        "Electronic Withdrawals"
        "Ending Balance"
    )
    local csummary

    while getopts ':f:k' opt;
    do
        case $opt in
            f) fp="$OPTARG" ;;
            k) get_keys=true ;;
            *)
                echo -e "Invalid argument: ${OPTARG}\nUsage: [f (file-path)]" >&2
                exit 1
                ;;
        esac
    done

    [[ "$get_keys" == true ]] && {
        printf '%s\n' "${CHECKING_SUMMARY_KEYS[@]}"
        return 0
    }
    
    checkDir -f "$fp" -D
    csummary=$(grepFiles -f "$fp" -p "." | awk '
        /Beginning Balance/             {bb = $NF}
        /Deposits and Additions/        {da = $NF}
        /ATM & Debit Card Withdrawals/  {aw = $NF}
        /Electronic Withdrawals/        {ew = $NF}
        /Ending Balance/                {eb = $NF}
        END {
            gsub(/[$,]/, "", bb)
            gsub(/[$,]/, "", da)
            gsub(/[$,]/, "", aw)
            gsub(/[$,]/, "", ew)
            gsub(/[$,]/, "", eb)
            print "Beginning Balance: " bb
            print "Deposits and Additions: " da
            print "ATM & Debit Card Withdrawals: " aw
            print "Electronic Withdrawals: " ew
            print "Ending Balance: " eb
        }
    ')

    if [[ -z "$csummary" ]]; then
        echo "No checking summary found in the provided file ($fp)." >&2
        exit 1
    else
        echo "$csummary"
    fi
}



getFiles(){
    terminator

    local opt
    local fp=""

    OPTIND=1
    while getopts ':f:h' opt;
    do
        case $opt in
            f) fp="$OPTARG" ;;
            h) help_page ;;
            *)
                echo -e "Invalid argument: ${OPTARG}\nUsage: [f (file-path) | e (echo-files)]" >&2
                exit 1
                ;;
        esac
    done

    dirHandler "$fp"
    echo "${CBS_PDF_FILES[@]}"
}


grepFiles(){ terminator; rgrepPDF "$@" ; }


getFunction(){
    terminator
    runDependencies

    local args=()
    local flag="$1"
    local get_files=false
    local grep_files=false
    local checking_summary=false

    function errMsg(){ echo -e "Invalid argument: $1\nUsage: [--get-files | --grep-files | --checking-summary | --help]" >&2 ;}
    function validateArgs(){
        for flag_arg in "$@";
        do
            if [[ "$flag_arg" = --* ]]; then
                [[ "$flag_arg" =~ --help ]] && help_page
                [[ "$flag_arg" =~ --get-files|--grep-files|--checking-summary ]] \
                    && echo "Cannot simultaneously use (--get-files | --grep-files | --checking-summary) flags together." >&2
                errMsg "$flag_arg"
                exit 1
            fi
        done
    }

    while [[ $# -gt 0 ]]; do
        if [[ -n "$flag" && "$flag" = --* ]]; then
            case "$flag" in
                --get-files)
                    get_files=true
                    shift
                    while [[ "$#" -gt 0 ]];
                    do
                        validateArgs "$@"
                        args+=("$1")
                        shift
                    done
                    ;;
                --grep-files)
                    grep_files=true
                    shift
                    while [[ "$#" -gt 0 ]];
                    do
                        validateArgs "$@"
                        args+=("$1")
                        shift
                    done
                    ;;
                --checking-summary)
                    checking_summary=true
                    shift
                    while [[ "$#" -gt 0 ]];
                    do
                        validateArgs "$@"
                        args+=("$1")
                        shift
                    done
                    ;;
                --help) help_page ;;
                *)
                    errMsg "$OPTARG" >&2
                    exit 1
                    ;;
            esac
        else
            errMsg "$flag" >&2
            exit 1
        fi
    done

    if [[ "$get_files" == true ]]; then
        getFiles "${args[@]}"
    elif [[ "$grep_files" == true ]]; then
        grepFiles "${args[@]}"
    elif [[ "$checking_summary" == true ]]; then
        checkingSummary "${args[@]}"
    else
        echo "No valid flag was provided. Please use '--help' flag for further assistance." >&2
        exit 1
    fi
}


if [[ "$0" != "${BASH_SOURCE[0]}" ]]; then
    export -f \
        getFunction getFiles \
        grepFiles checkingSummary
else
    getFunction "$@"
fi