from flask_wtf import Form
from flask_security.forms import LoginForm
from wtforms import validators, StringField, TextAreaField, DateField, DateTimeField, SelectField, FormField, FieldList
from wtforms.validators import InputRequired
from models import Break

class ExtendedLoginForm(LoginForm):
    email = StringField('Username or Email Address', [InputRequired()])

class EntryForm(Form):

    breaks = list(Break.select(Break.id, Break.name).tuples())
    breaks.insert(0, (0, ''))

    date = DateField("Date")
    started_at = DateTimeField("Started At", format='%H:%M')
    finished_at = DateTimeField("Finished At", format='%H:%M')
    
    break_for = SelectField("Break For", choices=breaks)
    
    #title = StringField("Title",[
    #    validators.Required(),
    #    validators.Length(max=80)
    #])
    #body = TextAreaField("Content",[validators.Required(),])
    #category = QuerySelectField("Category", query_factory=lambda: Category.query, allow_blank=True)
    #new_category = StringField("New Category")

class TimeSheetForm(Form):
    entries = FieldList(FormField(EntryForm), min_entries=7) #, max_entries=7)
    
    def fill(self, entries):
        for e in entries:
            self.entries.append_entry((e.date, e.started_at, e.finished_at, e.break_for.id if e.break_for else None))
            
    