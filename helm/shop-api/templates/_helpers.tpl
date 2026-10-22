{{- define "shop-api.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "shop-api.labels" -}}
app.kubernetes.io/name: {{ include "shop-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "shop-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "shop-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
