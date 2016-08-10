"""
The MIT License (MIT)
Copyright (c) 2014-2017 University of Bristol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.
"""

from utils import Printable


class Tool(Printable):
    def process_params(self, *args, **kwargs):
        raise NotImplementedError()

    def normalise_tool(self, *args, **kwargs):
        raise NotImplementedError()

    def normalise_kwargs(self, *args, **kwargs):
        raise NotImplementedError()

    def process_params(self, **kwargs):
        print('Defining a {} stream'.format(self.__class__.__name__))

        return [], dict(kwargs)

    def __str__(self):
        # TODO: @Meelis: Should this return __name__ or self.__class__.__name__ ?
        return self.__class__.__name__

    def __hash__(self):
        # TODO: @Meelis: should this return hash(__name__) or hash(self.__class__.__name__) ?
        return hash(self.__class__.__name__)