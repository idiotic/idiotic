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

# Features #

*Note that idiotic is currently in alpha. Some parts in this section
describes its design ideals and goals, rather than its current
state. They may be incomplete, buggy, or completely absent at this
time, but they will eventually exist. Check the documentation for
what is currently available.*

## Uniform Configuration ##

Every configuration file in idiotic is just a specialized Python
module. If you're not familiar with Python, the syntax needed to
configure Generally, you just need to define items, rules, or constants,
but you can also get creative and define these programatically if you
need to (or do anything else you need to -- it's Python!).

## Simple and Intuitive Rule Creation ##

idiotic uses [schedule](https://github.com/dbader/schedule) for its
simple, human-friendly time-based job scheduling syntax, and a simple
decorator-based syntax for binding to any event in the system. Rule
bindings can also be augmented to make some common patterns
encountered in home automation extremely simple and reduce the need
for boilerplate code.

Want to do something whenever an item changes?

    @bind(Change(item.foo)
	def rule(event):
	    print("Do something!")

Want to call a rule every Tuesday at 7:15pm?

    @bind(Schedule(scheduler.every().tuesday.at("19:25")))
	def rule(event):
	    print("Wooo, party time!")

Want to control a light with a motion sensor to turn off after five
minutes?

    @bind(Command(items.motion_sensor))
    @augment(Delay(item=items.motion_sensor, command="OFF", period=300))
	def rule(event):
	    items.light.command(event.command)

## Flexible Web-interface Creation ##

With idiotic, you can quickly create rich, dynamic control panels and
status displays without touching any HTML, CSS, or Javascript -- or
you can use your own CSS, HTML, and Javascript to enhance and
customize the web interface if you want to.

## Distributed Architecture ##

With the advent of cheap physical computing, a smarthome can have many
devices attached to many different physical computers. With a
centralized system, this necessitates the creation of an additional
layer of communication. With idiotic, you can simply run an instance
on each computer whose devices you want to include, and then control
them from any other instance as though they were local.

## REST API ##

idiotic comes with a full-featured REST API that might end up being
backwards-compatible with OpenHAB's.... _This doesn't exist yet._
