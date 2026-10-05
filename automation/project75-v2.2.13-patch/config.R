env_bool <- function(name, default = TRUE) {
  value <- trimws(tolower(Sys.getenv(name, unset = "")))
  if (!nzchar(value)) return(default)
  if (value %in% c("1", "true", "yes", "y")) return(TRUE)
  if (value %in% c("0", "false", "no", "n")) return(FALSE)
  stop("Invalid boolean environment variable ", name, ": ", value)
}

DCEPD_CONFIG <- list(
  version = "2.2.13",
  dry_run = env_bool("DCEPD_DRY_RUN", TRUE),
  timezone = "Africa/Dar_es_Salaam",

  redcap_url = "https://utafiti.muhas.ac.tz/api/",
  project75_token_env = "REDCAP_PROJECT75_TOKEN",
  project79_token_env = "REDCAP_PROJECT79_TOKEN",

  run_log_instrument = "course_run_log",
  admin_control_instrument = "accreditation_publication_control",
  project79_choice_field = "applied_course_id",

  dormant_after_years = 2L,
  reaccreditation_years = 3L,
  due_soon_months = 6L,
  year_choice_buffer = 2L,

  stop_on_qc_error = TRUE,
  enable_project75_metadata_sync = TRUE,
  enable_project79_choice_sync = TRUE,
  metadata_write_mode = "read_only",

  record_import_batch_size = 20L,
  verify_each_record_batch = TRUE,

  expected_project75_field_count = 80L,
  expected_project79_field_count = 73L,
  expected_project75_forms = c("course_registry", "course_run_log", "accreditation_publication_control", "public_catalogue_details"),
  expected_project79_forms = c("short_course_application", "participant_selection_certification"),

  output_dir = "output",
  proposed_archive_dir = file.path("archive", "proposed"),
  verified_archive_dir = file.path("archive", "verified"),
  log_dir = "logs",
  crosswalk_file = file.path("config", "project79_course_crosswalk.csv")
)
