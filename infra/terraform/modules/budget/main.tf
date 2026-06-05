# ── Billing Budget ────────────────────────────────────────────────────────────
# Alerts at 50%, 75%, 90%, 100% of monthly spend.
# 100% threshold uses FORECASTED_SPEND to alert before overage.

resource "google_billing_budget" "budget" {
  provider        = google-beta
  billing_account = var.billing_account_id
  display_name    = "ClearSettle ${var.env} Monthly Budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount_usd)
    }
  }

  # 50% — informational
  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  # 75% — warning
  threshold_rules {
    threshold_percent = 0.75
    spend_basis       = "CURRENT_SPEND"
  }

  # 90% — alert
  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }

  # 100% — critical (based on forecast to get ahead of overage)
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = []
    disable_default_iam_recipients   = false

    pubsub_topic = var.alert_pubsub_topic != "" ? var.alert_pubsub_topic : null
  }
}
