# Dataset: Sample Call Transcripts

This dataset contains a set of sample calls for use in the AI-Assisted Call Review System exercise.

Each call includes:

- `id`: unique identifier
- `goal`: the intended purpose of the call
- `transcript`: a text representation of the call (may be incomplete or noisy)
- `metadata`: basic contextual information (e.g., duration)

## Purpose

The dataset is designed to reflect a range of real-world scenarios, including:

- Clear, straightforward outcomes
- Ambiguous or conflicting signals
- Noisy or incomplete transcripts
- Edge cases such as voicemail, wrong number, or dropped calls

Not all calls will have a single obvious interpretation.

## Important Considerations

When working with this dataset, you should assume:

- Transcripts may not fully capture what happened
- Some calls may not cleanly map to a single outcome
- The same call may have multiple relevant aspects (e.g., connection status, user intent, escalation)
- The cost of being wrong may vary depending on the situation

You should take these factors into account when designing your system.

## Expectations

You are not expected to:

- Infer a "correct" label for each call
- Match any predefined taxonomy

Instead, you should:

- Define your own outcome structure
- Decide how to handle ambiguity and uncertainty
- Determine which calls require human review

## Extending the Dataset

As part of the exercise, you should add at least 5 additional calls that:

- Represent edge cases or failure modes
- Challenge your system's assumptions
- Highlight limitations in your approach