"""Legacy AI integration disabled for the maintenance-only Stage 1 pilot."""


class LLMDiagnosticAdvisor:
    @classmethod
    def generate_diagnosis(cls, machine_id, telemetry_context):
        raise RuntimeError('AI diagnostics are disabled. Stage 1 uses verified equipment records, maintenance history and private manuals only.')
