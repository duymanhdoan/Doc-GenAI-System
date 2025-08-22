{{/*
Expand the name of the chart.
*/}}
{{- define "monitoring-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "monitoring-stack.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "monitoring-stack.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "monitoring-stack.labels" -}}
helm.sh/chart: {{ include "monitoring-stack.chart" . }}
{{ include "monitoring-stack.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "monitoring-stack.selectorLabels" -}}
app.kubernetes.io/name: {{ include "monitoring-stack.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Generate config checksum for pod annotations
This ensures pods restart when configuration changes
*/}}
{{- define "monitoring-stack.configChecksum" -}}
{{- $service := .service -}}
{{- $context := .context -}}
{{- $configData := "" -}}
{{- if eq $service "prometheus" -}}
{{- $configData = index $context.Values "prometheus" "config" | default dict | toYaml -}}
{{- else if eq $service "grafana" -}}
{{- $configData = index $context.Values "grafana" "config" | default dict | toYaml -}}
{{- else if eq $service "alertmanager" -}}
{{- $configData = index $context.Values "alertmanager" "config" | default dict | toYaml -}}
{{- else if eq $service "elasticsearch" -}}
{{- $configData = index $context.Values "elasticsearch" "config" | default dict | toYaml -}}
{{- else if eq $service "kibana" -}}
{{- $configData = index $context.Values "kibana" "config" | default dict | toYaml -}}
{{- else if eq $service "filebeat" -}}
{{- $configData = index $context.Values "filebeat" "config" | default dict | toYaml -}}
{{- else if eq $service "jaeger" -}}
{{- $configData = index $context.Values "jaeger" "config" | default dict | toYaml -}}
{{- else -}}
{{- $configData = "default-config" -}}
{{- end -}}
{{- sha256sum $configData -}}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "monitoring-stack.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "monitoring-stack.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}