# bao-agent de la prod (stack ai-jobs) : rend /run/ai-jobs/.env (tmpfs) pour bao-deploy.sh.
# Installé par stack-sync dans /etc/bao/ai-jobs/ ; ce qu'il peut lire est borné par la policy
# ai-jobs-prod-read (secret/ai-jobs/prod/*), créée hors CI (vps-soc-config, ai-jobs/setup-bao.sh).
pid_file = "/run/ai-jobs/agent.pid"

vault {
  address = "http://127.0.0.1:8200"
}

auto_auth {
  method "approle" {
    config = {
      role_id_file_path                   = "/etc/bao/ai-jobs/role_id"
      secret_id_file_path                 = "/etc/bao/ai-jobs/secret_id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink "file" {
    config = {
      path = "/run/ai-jobs/.bao-token"
      mode = 0600
    }
  }
}

template_config {
  exit_on_retry_failure         = true
  static_secret_render_interval = "1h"
}

template {
  destination = "/run/ai-jobs/.env"
  perms       = "0640"
  contents    = <<EOT
{{ with secret "secret/data/ai-jobs/prod/mysql" }}
MYSQL_DATABASE={{ .Data.data.MYSQL_DATABASE }}
MYSQL_USER={{ .Data.data.MYSQL_USER }}
MYSQL_PASSWORD={{ .Data.data.MYSQL_PASSWORD }}
MYSQL_ROOT_PASSWORD={{ .Data.data.MYSQL_ROOT_PASSWORD }}
{{ end }}
EOT
}
