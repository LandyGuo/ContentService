from django.core.management.base import BaseCommand
from contentservice import scripts
from contentservice.utils import get_exception_info

class Command(BaseCommand):
    help = ('RunScript')

    def handle(self, *args, **options):
        if len(args) < 1:
            self.hint()
            return

        command = args[0]
        _args = []
        for i in range(1, len(args)):
            arg = args[i]
            if arg.isdigit():
                arg = int(arg)
            _args.append(arg)

        func = getattr(scripts, command)
        if not callable(func):
            self.hint()
        else:
            try:
                func(*_args)
            except SystemExit:
                print 'process exit.'
            except:
                print get_exception_info()

    def hint(self):
        print "Usage: runscript name [params]\n"
        print "Available scripts:"
        for name in dir(scripts):
            attr = getattr(scripts, name)
            if callable(attr):
                print name
