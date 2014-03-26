class ExternalCommandBuilder(object):

    def __init__(self, command_name, project):
        self.command_name = command_name
        self.parts = [command_name]
        self.project = project

    def has_argument(self, argument):
        self.parts.append(argument)
        return self

    def formatted_with_property(self, property_name):
        property_value = self.project.get_property(property_name)
        self.parts[-1] = self.parts[-1].format(property_value)
        return self

    def formatted_with_truthy_property(self, property_name):
        return self.formatted_with_property(property_name).only_if_property_is_truthy(property_name)

    def only_if_property_is_truthy(self, property_name):
        property_value = self.project.get_property(property_name)
        if not property_value:
            del self.parts[-1]
        return self

    @property
    def as_string(self):
        return ' '.join(self.parts)
