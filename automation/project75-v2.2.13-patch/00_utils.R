clean_text <- function(x) {
  x <- trimws(as.character(x))
  x[x %in% c("", "NA", "N/A", "NULL", "null")] <- NA_character_
  x
}

parse_redcap_date <- function(x) {
  x <- clean_text(x)
  suppressWarnings(as.Date(
    lubridate::parse_date_time(
      x,
      orders = c("Ymd", "Y-m-d", "dmy", "d/m/Y", "dmY", "mdy", "m/d/Y"),
      quiet = TRUE
    )
  ))
}

parse_redcap_datetime <- function(x) {
  x <- clean_text(x)
  suppressWarnings(
    lubridate::parse_date_time(
      x,
      orders = c(
        "Ymd HMS", "Y-m-d H:M:S",
        "dmy HMS", "d/m/Y H:M:S",
        "Ymd HM", "Y-m-d H:M",
        "dmy HM", "d/m/Y H:M"
      ),
      quiet = TRUE
    )
  )
}

parse_numeric_safe <- function(x) {
  x <- clean_text(x)
  out <- suppressWarnings(
    readr::parse_number(
      x,
      locale = readr::locale(grouping_mark = ",")
    )
  )
  out[is.na(x)] <- NA_real_
  out
}

fmt_date <- function(x) {
  ifelse(is.na(x), "", format(as.Date(x), "%Y-%m-%d"))
}

fmt_datetime_api <- function(x = Sys.time()) {
  format(x, "%Y-%m-%d %H:%M:%S")
}

normalise_char <- function(x) {
  x <- as.character(x)
  x[is.na(x)] <- ""
  trimws(x)
}

values_equal <- function(a, b) {
  identical(normalise_char(a), normalise_char(b))
}

fiscal_quarter_code <- function(date_value) {
  m <- lubridate::month(date_value)
  dplyr::case_when(
    is.na(date_value) ~ "",
    m %in% 7:9 ~ "1",
    m %in% 10:12 ~ "2",
    m %in% 1:3 ~ "3",
    m %in% 4:6 ~ "4",
    TRUE ~ ""
  )
}

fiscal_year_code <- function(date_value) {
  y <- lubridate::year(date_value)
  m <- lubridate::month(date_value)
  start_year <- dplyr::if_else(
    is.na(date_value),
    NA_integer_,
    dplyr::if_else(m >= 7L, y, y - 1L)
  )
  end_short <- (start_year + 1L) %% 100L
  ifelse(
    is.na(start_year),
    "",
    sprintf("FY%04d_%02d", start_year, end_short)
  )
}

fiscal_year_label_from_start <- function(start_year) {
  sprintf("%04d/%02d", start_year, (start_year + 1L) %% 100L)
}

month_code <- function(date_value) {
  ifelse(is.na(date_value), "", as.character(lubridate::month(date_value)))
}

parse_choices <- function(choice_string) {
  choice_string <- clean_text(choice_string)
  if (is.na(choice_string)) {
    return(tibble::tibble(value = character(), label = character()))
  }
  parts <- strsplit(choice_string, "\\|", fixed = FALSE)[[1]]
  parts <- trimws(parts)
  parts <- parts[nzchar(parts)]
  out <- lapply(parts, function(part) {
    comma <- regexpr(",", part, fixed = TRUE)[1]
    if (comma < 1) {
      return(c(value = trimws(part), label = ""))
    }
    c(
      value = trimws(substr(part, 1, comma - 1)),
      label = trimws(substr(part, comma + 1, nchar(part)))
    )
  })
  tibble::as_tibble(do.call(rbind, out))
}

build_choices <- function(choice_df) {
  if (nrow(choice_df) == 0) return("")
  paste0(choice_df$value, ", ", choice_df$label, collapse = " | ")
}

merge_choices_from_source <- function(source_string, target_string) {
  src <- parse_choices(source_string)
  tgt <- parse_choices(target_string)
  run_only <- tgt[!tgt$value %in% src$value, , drop = FALSE]
  merged <- dplyr::bind_rows(src, run_only)
  build_choices(merged)
}

log_line <- function(log_file, ...) {
  msg <- paste0(...)
  line <- paste0("[", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "] ", msg)
  cat(line, "\n")
  cat(line, "\n", file = log_file, append = TRUE)
  invisible(line)
}

write_csv_safe <- function(x, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  readr::write_csv(x, path, na = "")
  invisible(path)
}

snapshot_copy <- function(files, destination_dir) {
  dir.create(destination_dir, recursive = TRUE, showWarnings = FALSE)
  for (f in files) {
    if (file.exists(f)) {
      file.copy(f, file.path(destination_dir, basename(f)), overwrite = TRUE)
    }
  }
  invisible(destination_dir)
}

course_code_year <- function(x) {
  x <- clean_text(x)
  suppressWarnings(as.integer(sub("^.*?/([0-9]{4})$", "\\1", x)))
}

status_rank <- function(code) {
  code <- clean_text(code)
  dplyr::case_when(
    code == "2" ~ 4L,
    code == "1" ~ 3L,
    code == "0" ~ 2L,
    code == "3" ~ 1L,
    TRUE ~ 0L
  )
}

status_code_from_rank <- function(rank) {
  dplyr::case_when(
    rank >= 4L ~ "2",
    rank == 3L ~ "1",
    rank == 2L ~ "0",
    rank == 1L ~ "3",
    TRUE ~ ""
  )
}

safe_integer <- function(x) {
  suppressWarnings(as.integer(clean_text(x)))
}

assert_restored_project_structure <- function(meta75, meta79, raw75, raw79, cfg) {
  issues <- character()

  forms75 <- unique(clean_text(meta75$form_name))
  forms75 <- sort(forms75[!is.na(forms75)])
  forms79 <- unique(clean_text(meta79$form_name))
  forms79 <- sort(forms79[!is.na(forms79)])

  if (nrow(meta75) != cfg$expected_project75_field_count) {
    issues <- c(issues, paste0("Project 75 field count is ", nrow(meta75),
      "; expected ", cfg$expected_project75_field_count, "."))
  }
  if (nrow(meta79) != cfg$expected_project79_field_count) {
    issues <- c(issues, paste0("Project 79 field count is ", nrow(meta79),
      "; expected ", cfg$expected_project79_field_count, "."))
  }

  expected75 <- sort(cfg$expected_project75_forms)
  expected79 <- sort(cfg$expected_project79_forms)

  if (!identical(forms75, expected75)) {
    issues <- c(issues, paste0("Project 75 instruments/forms are [",
      paste(forms75, collapse = ", "), "]; expected [",
      paste(expected75, collapse = ", "), "]."))
  }
  if (!identical(forms79, expected79)) {
    issues <- c(issues, paste0("Project 79 instruments/forms are [",
      paste(forms79, collapse = ", "), "]; expected [",
      paste(expected79, collapse = ", "), "]."))
  }

  required75 <- c("record_id", "redcap_repeat_instrument", "redcap_repeat_instance")
  missing75 <- setdiff(required75, names(raw75))
  if (length(missing75) > 0) {
    issues <- c(issues, paste0("Project 75 export is missing REDCap system columns: ",
      paste(missing75, collapse = ", "), "."))
  }

  if (length(missing75) == 0) {
    repeat75 <- unique(clean_text(raw75$redcap_repeat_instrument))
    repeat75 <- sort(repeat75[!is.na(repeat75)])
    allowed_repeat75 <- sort(c(cfg$run_log_instrument, cfg$admin_control_instrument))
    unexpected_repeat75 <- setdiff(repeat75, allowed_repeat75)
    if (length(unexpected_repeat75) > 0) {
      issues <- c(issues, paste0("Project 75 contains unexpected repeating instrument(s): ",
        paste(unexpected_repeat75, collapse = ", "), "."))
    }
  }

  if (!"applied_course_id" %in% names(raw79)) {
    issues <- c(issues, "Project 79 export is missing applied_course_id.")
  }

  if (length(issues) > 0) {
    stop("POST-RECOVERY STRUCTURE GUARD FAILED:\n- ",
      paste(issues, collapse = "\n- "),
      "\nNo record writes were attempted.")
  }
  invisible(TRUE)
}
