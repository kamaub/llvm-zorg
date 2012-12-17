from buildbot.schedulers import basic
from buildbot.schedulers import triggerable
from buildbot.process.properties import WithProperties
from buildbot.changes.filter import ChangeFilter

# Load the phase information.
from phase_config import phases

def get_phase_stages(phase):
    """get_phase_stages() -> [(normal builders, experimental builders), ...]

    Split a phase's builders into the list of serial stages, and separate
    experimental builders from non-exerpeimntal ones."""

    builders = dict((b['name'], b)
                    for b in phase['builders'])

    # Each entry in the stage parameter should be a list of builder names.
    stages = []
    for stage in phase.get('stages', []):
        stages.append([builders.pop(name)
                       for name in stage])

    # Add any remaining builders to the final stage.
    stages.append(builders.values())

    # Split the builder types.
    split_stages = []
    for stage in stages:
        normal_builders = []
        experimental_builders = []
        for b in stage:
            if b['category'] != 'experimental':
                normal_builders.append(b)
            else:
                experimental_builders.append(b)
        split_stages.append( (normal_builders, experimental_builders) )

    return split_stages

def get_schedulers():
    first_phase = phases[0]
    last_phase = phases[-1]

    # The VC scheduler initiates the first phase.
    # Each phase, in turn, triggers the next phase,
    # until the fianl phase

    for phase in phases:
        phase_name = 'phase%d' % phase['number']
        my_filter = ChangeFilter(category = phase_name)
        if phase == first_phase:
            delay=120
        else:
            delay=15
        
        yield basic.AnyBranchScheduler(
            name = phase_name, treeStableTimer=delay,
            change_filter = my_filter,
            builderNames = ['phase%d - %s' % (phase['number'], phase['name'])],
            )

    # Add triggers for initiating the builds in each phase.
    for phase in phases:

        # Split the phase builders into separate stages.
        split_stages = get_phase_stages(phase)
        for i, (normal, experimental) in enumerate(split_stages):
            # Add the normal trigger, if used.
            if normal:
                yield triggerable.Triggerable(
                    name = 'phase%d-stage%d' % (phase['number'], i),
                    builderNames = [b['name'] for b in normal])

            # Add the experimental trigger, if used.
            if experimental:
                yield triggerable.Triggerable(
                    name = 'phase%d-stage%d-experimental' % (phase['number'],
                                                             i),
                    builderNames = [b['name'] for b in experimental])

    # Add a final trigger to trigger the validated build scheduler.
    phase_name = 'GoodBuild'
    my_filter = ChangeFilter(category = phase_name)
    yield basic.AnyBranchScheduler(
            name = phase_name, treeStableTimer=5,
            builderNames = ['Validated Build',],
            change_filter = my_filter,
            )
