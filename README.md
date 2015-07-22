# Introduction #

The idiotic distributed internet of things inhabitance controller
(idiotic), aims to be an extremely extensible, capable, and most
importantly developer-and-user-friendly solution for mashing together
a wide assortment of existing home automation technologies into
something which is useful as a whole. It is also intended to provide a
relatively painless transition for users of
[OpenHAB](https://github.com/openhab/openhab), its inspiration.

# Philosophy #

My first experience with a centralized home automation system was with
the aforementioned OpenHAB. At first, I was very excited to find
something which could finally integrate the hodge-podge of devices,
protocols, and random scripts that previously controlled the house in
their own separate, disconnected ways. However, I ran into walls at
every step: the syntax was inflexible and inconsistent, the
documentation was incomplete, and I found myself repeating code
constantly. There were no bindings for much of the technology I had
hoped to integrate, and creating a new one was needlessly complex. And
because almost all my sensors and other devices were attached to a
device other than my OpenHAB server, I was eventually just using the
HTTP binding to control external scripts I wrote myself.

I decided that this was not the way things should work. Implementing
new bindings should be as easy as dropping a couple functions into a
directory. Rules shouldn't be written in
[the most enterprisey scripting language ever](http://xtend-lang.org).
Each configuration file shouldn't have its own completely unique
syntax. A system designed for controlling something as complex as a
home should be *flexible*!

idiotic is designed with these goals in mind:

* Be stupidly simple to configure, use, and extend
* Be flexible
* Be consistent
* Be reusable
* Be modular

# Features #

*Note that idiotic is currently in a very immature beta version. It
will at times have incomplete or missing features, weird bugs and
inconsistencies, and lack support for pretty much everything.* If
you're not the kind of person who wants something that was written
mostly at 4AM in control of your house and all the things in it, then
you should probably hold off on using idiotic. If you're the kind of
person who enjoys filing bug reports or even making pull requests and
won't sue if your coffee machine turns against you because of a typo,
then you're probably going to like idiotic. If you're feeling
particularly adventurous, you could even head over to
[idiotic-modules](https://github.com/umbc-hackafe/idiotic-modules/)
and see if you could help write modules to support more third-party
protocols.

With that said, I'm currently using idiotic for my own house and it
hasn't yet resulted in catastrophe. The features which have been
implemented are almost stable at this point and idiotic is designed in
a way that tends to eliminate single points of failure.

## Uniform Configuration ##

Every configuration file in idiotic is just a specialized Python
module. Generally, you just need to define items, rules, or constants,
but you can also get creative and define these programatically if you
need to (or do anything else you need to -- it's just Python!).

## Lightweight and Modular ##

Because of the need for flexibility, idiotic itself aims to be mostly
infrastructure. The rest is up to the module system, which means that
anyone can add core functionality into idiotic without having to
modify the source code directly. There is a basic set of modules that
are included with idiotic in packages for convenience, but these can
be replaced or removed if you desire. So adding support for new home
automation protocols can be done externally by just dropping a python
script into a directory, but still with all the power of the
underlying codebase.

## Simple and Intuitive Rule Creation ##

idiotic uses [schedule](https://github.com/dbader/schedule) for its
simple, human-friendly time-based job scheduling syntax, and a simple
decorator-based syntax for binding to any event in the system. Rule
bindings can also be augmented to make some common patterns
encountered in home automation extremely simple and reduce the need
for boilerplate code.

Want to do something whenever an item changes?

    @bind(Change(item.foo))
	def rule(event):
	    print("Wow, how exciting!")

Want to call a rule every Tuesday at 7:15pm?

    @bind(Schedule(scheduler.every().tuesday.at("19:25")))
	def rule(event):
	    print("Wooo, party time!")

Want to control a light with a motion sensor to turn off after five
minutes?

    @bind(Command(items.motion_sensor))
    @augment(Delay(Command(items.motion_sensor, "OFF"), period=300),
	               cancel=Command(items.motion_sensor, "ON"))
	def rule(event):
	    items.light.command(event.command)

Have a lot of lights? Just use a loop!

    for sensor, light in [(items.some_sensor, items.some_light),
	                      (items.another_sensor, items.another_light),
                          (items.last_sensor, items.last_light)]:
		# Weird scope stuff makes us use closures
		def closure(s, l):
	        @bind(Command(sensor))
		    @augment(Delay(Command(s, "OFF"), period=300),
			         cancel=Command(s, "ON"))
			def rule(event):
			    l.command(event.command)
		closure(s, l)

## Flexible Web-interface Creation ##

With idiotic, you can quickly create rich, dynamic control panels and
status displays without touching any HTML, CSS, or Javascript -- or
you can use your own CSS, HTML, and Javascript to enhance and
customize the web interface however you like.

## Distributed Architecture ##

With the advent of cheap physical computing, a smarthome can have many
devices attached to many different physical computers. With a
centralized system, this necessitates the creation of an additional
layer of communication. With idiotic, you can simply run an instance
on each computer whose devices you want to include, and then control
them from any other instance as though they were local. _This is
pretty close to being complete, but lacks some arguably important
features._

## REST API ##

idiotic comes with an easily extensible REST API, with an optional
compatibility layer for mimicking OpenHAB's REST API.
