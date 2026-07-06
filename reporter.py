from config import OutputConfig


class Reporter:
    def __init__(self, output_config: OutputConfig) -> None:
        self.output_config = output_config
        self.directory = self.output_config.directory
        self.use_timestamp = output_config.timestamp

    def report(self, data) -> None:
        for format in self.output_config.formats:
            match format:
                case 'csv':
                    self.write_csv_report(data)
                case 'json':
                    self.write_json_report(data)
                case 'md':
                    self.write_md_report(data)
                case _:
                    ...

    def write_csv_report(self, data) -> None:
        ...

    def write_json_report(self, data) -> None:
        ...

    def write_md_report(self, data) -> None:
        ...