derive_project75 <- function(raw, cfg, reference_date) {
  required_system <- c(
    "record_id", "redcap_repeat_instrument", "redcap_repeat_instance"
  )
  miss <- setdiff(required_system, names(raw))
  if (length(miss) > 0) {
    stop("Project 75 export missing REDCap system fields: ", paste(miss, collapse = ", "))
  }

  # Administrative repeat instruments are intentionally excluded:
  # master rows have blank repeat instrument and delivery rows must match
  # cfg$run_log_instrument exactly.
  master <- raw |>
    dplyr::mutate(
      .record_id = clean_text(record_id),
      .repeat_instrument = clean_text(redcap_repeat_instrument)
    ) |>
    dplyr::filter(!is.na(.record_id), is.na(.repeat_instrument))

  if (anyDuplicated(master$.record_id) > 0) {
    stop("Duplicate Project 75 master record IDs found.")
  }

  runs <- raw |>
    dplyr::mutate(
      .record_id = clean_text(record_id),
      .repeat_instrument = clean_text(redcap_repeat_instrument),
      .repeat_instance = clean_text(redcap_repeat_instance),
      .run_start_date = parse_redcap_date(run_start_date),
      .run_participants = parse_numeric_safe(run_participants),
      .run_income_tsh = parse_numeric_safe(run_income_tsh)
    ) |>
    dplyr::filter(
      !is.na(.record_id),
      .repeat_instrument == cfg$run_log_instrument
    )

  if (nrow(runs) > 0 && any(is.na(runs$.repeat_instance))) {
    stop("One or more Course Run Log rows have no redcap_repeat_instance.")
  }

  dup_repeat <- runs |>
    dplyr::count(.record_id, .repeat_instrument, .repeat_instance) |>
    dplyr::filter(n > 1)
  if (nrow(dup_repeat) > 0) {
    stop("Duplicate Course Run Log repeat keys found.")
  }

  valid_runs <- runs |>
    dplyr::filter(!is.na(.run_start_date))

  run_summary <- valid_runs |>
    dplyr::group_by(.record_id) |>
    dplyr::summarise(
      valid_run_count = dplyr::n(),
      first_date_conducted_calc = min(.run_start_date),
      last_date_conducted_calc = max(.run_start_date),
      total_participants_calc = if (all(is.na(.run_participants))) {
        NA_real_
      } else {
        sum(.run_participants, na.rm = TRUE)
      },
      total_income_tsh_calc = if (
        all(is.na(.run_income_tsh)) ||
        all(is.na(.run_income_tsh) | .run_income_tsh <= 0)
      ) {
        NA_real_
      } else {
        sum(.run_income_tsh, na.rm = TRUE)
      },
      .groups = "drop"
    )

  m <- master |>
    dplyr::transmute(
      record_id = .record_id,
      course_name = clean_text(course_name),
      current_course_code = clean_text(course_code),
      date_submitted_d = parse_redcap_date(date_submitted),
      review_sent_date_d = parse_redcap_date(review_sent_date),
      reviewer_1_v = clean_text(reviewer_1),
      reviewer_2_v = clean_text(reviewer_2),
      accreditation_date_d = parse_redcap_date(accreditation_date),
      accreditation_date_first_d = parse_redcap_date(accreditation_date_first),
      approval_date_d = parse_redcap_date(approval_date),
      approval_reference_v = clean_text(approval_reference),
      course_school_code_v = clean_text(course_school_code),
      current_course_status = clean_text(course_status),
      current_times_conducted = clean_text(times_conducted),
      current_first_date_conducted = parse_redcap_date(first_date_conducted),
      current_last_date_conducted = parse_redcap_date(last_date_conducted),
      current_total_participants = parse_numeric_safe(total_participants),
      current_total_income_tsh = parse_numeric_safe(total_income_tsh),
      current_interested_applicants = clean_text(interested_applicants),
      current_interested_applicants_updated_at = clean_text(interested_applicants_updated_at)
    ) |>
    dplyr::left_join(run_summary, by = c("record_id" = ".record_id")) |>
    dplyr::mutate(
      valid_run_count = dplyr::coalesce(valid_run_count, 0L),

      expected_accreditation_date_first = dplyr::case_when(
        !is.na(accreditation_date_first_d) ~ fmt_date(accreditation_date_first_d),
        !is.na(accreditation_date_d) ~ fmt_date(accreditation_date_d),
        TRUE ~ ""
      ),

      expected_course_code = dplyr::case_when(
        !is.na(current_course_code) ~ current_course_code,
        !is.na(accreditation_date_d) &
          expected_accreditation_date_first != "" &
          !is.na(course_school_code_v) &
          !is.na(safe_integer(record_id)) ~ paste0(
            "DCEPD/",
            course_school_code_v,
            "/",
            sprintf("%03d", safe_integer(record_id)),
            "/",
            lubridate::year(as.Date(expected_accreditation_date_first))
          ),
        TRUE ~ ""
      ),

      reviewer_assigned =
        !is.na(reviewer_1_v) | !is.na(reviewer_2_v),

      review_evidence =
        !is.na(review_sent_date_d) & reviewer_assigned,

      formal_accreditation_evidence =
        !is.na(accreditation_date_d),

      legacy_accreditation_evidence =
        expected_course_code != "" &
        !grepl("/1900$", expected_course_code) &
        !is.na(accreditation_date_d) &
        current_course_status %in% c("1", "2"),

      accreditation_evidence =
        formal_accreditation_evidence | legacy_accreditation_evidence,

      evidence_status_rank = dplyr::case_when(
        valid_run_count > 0 ~ 4L,
        accreditation_evidence ~ 3L,
        review_evidence ~ 2L,
        !is.na(date_submitted_d) ~ 1L,
        TRUE ~ 0L
      ),

      expected_course_status = status_code_from_rank(
        pmax(status_rank(current_course_status), evidence_status_rank)
      ),

      accreditation_due_date =
        accreditation_date_d %m+% lubridate::period(years = cfg$reaccreditation_years),

      completed_accreditation =
        formal_accreditation_evidence | legacy_accreditation_evidence,

      expected_accreditation_status = dplyr::case_when(
        !completed_accreditation &
          (valid_run_count > 0 | grepl("/1900$", expected_course_code)) ~ "4",
        !completed_accreditation ~ "5",
        reference_date > accreditation_due_date ~ "3",
        accreditation_due_date <=
          (reference_date %m+% lubridate::period(months = cfg$due_soon_months)) ~ "2",
        TRUE ~ "1"
      ),

      expected_curriculum_type = dplyr::case_when(
        expected_accreditation_status %in% c("1", "2") ~ "2",
        expected_accreditation_status == "3" ~ "1",
        TRUE ~ ""
      ),

      dormant_cutoff =
        reference_date %m-% lubridate::period(years = cfg$dormant_after_years),

      expected_dormant_flag = dplyr::case_when(
        valid_run_count == 0 ~ "",
        last_date_conducted_calc < dormant_cutoff ~ "1",
        TRUE ~ "0"
      ),

      expected_public_catalogue = dplyr::case_when(
        expected_accreditation_status %in% c("1", "2") &
          expected_dormant_flag != "1" ~ "1",
        TRUE ~ "0"
      ),

      expected_accreditation_year = ifelse(
        is.na(accreditation_date_d),
        "",
        as.character(lubridate::year(accreditation_date_d))
      ),

      expected_accreditation_fiscal_quarter =
        fiscal_quarter_code(accreditation_date_d),

      expected_accreditation_fiscal_year =
        fiscal_year_code(accreditation_date_d),

      expected_times_conducted =
        as.character(valid_run_count),

      expected_first_date_conducted =
        fmt_date(first_date_conducted_calc),

      expected_last_date_conducted = dplyr::case_when(
        is.na(current_last_date_conducted) ~ fmt_date(last_date_conducted_calc),
        is.na(last_date_conducted_calc) ~ fmt_date(current_last_date_conducted),
        current_last_date_conducted >= last_date_conducted_calc ~
          fmt_date(current_last_date_conducted),
        TRUE ~ fmt_date(last_date_conducted_calc)
      ),

      expected_total_participants = ifelse(
        is.na(total_participants_calc),
        "",
        formatC(total_participants_calc, format = "f", digits = 0)
      ),

      expected_total_income_tsh = ifelse(
        is.na(total_income_tsh_calc),
        "",
        formatC(total_income_tsh_calc, format = "f", digits = 0)
      )
    )

  expected_master <- m |>
    dplyr::transmute(
      record_id,
      accreditation_date_first = expected_accreditation_date_first,
      course_code = expected_course_code,
      course_status = expected_course_status,
      dormant_flag = expected_dormant_flag,
      curriculum_type = expected_curriculum_type,
      accreditation_status = expected_accreditation_status,
      public_catalogue = expected_public_catalogue,
      accreditation_year = expected_accreditation_year,
      accreditation_fiscal_quarter = expected_accreditation_fiscal_quarter,
      accreditation_fiscal_year = expected_accreditation_fiscal_year,
      times_conducted = expected_times_conducted,
      first_date_conducted = expected_first_date_conducted,
      last_date_conducted = expected_last_date_conducted,
      total_participants = expected_total_participants,
      total_income_tsh = expected_total_income_tsh,
      interested_applicants = dplyr::coalesce(current_interested_applicants, ""),
      interested_applicants_updated_at =
        dplyr::coalesce(current_interested_applicants_updated_at, "")
    )

  expected_runs <- runs |>
    dplyr::transmute(
      record_id = .record_id,
      redcap_repeat_instrument = .repeat_instrument,
      redcap_repeat_instance = .repeat_instance,
      run_batch_id = paste0(.record_id, "-", .repeat_instance),
      calendar_year = ifelse(
        is.na(.run_start_date),
        "",
        as.character(lubridate::year(.run_start_date))
      ),
      month = month_code(.run_start_date),
      fiscal_quarter = fiscal_quarter_code(.run_start_date),
      fiscal_year = fiscal_year_code(.run_start_date)
    )

  list(
    master_source = m,
    run_source = runs,
    expected_master = expected_master,
    expected_runs = expected_runs,
    invalid_run_rows = runs |> dplyr::filter(is.na(.run_start_date))
  )
}
