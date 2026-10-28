# Text as Data Module: Detailed Rubric

Total: 20 points (of 28 available -- this allows multiple paths through the module)

No single tool or method is required. A notebook can earn full marks with regular expressions and
careful reading, with classifiers, with search and RAG, with structured extraction, or with any
mix of them. You may automate any step that a model can do well. You are graded on the decisions
you make, how you check them, and how well you tell the story.

## 1. Defining the question and the corpus (**5 points**)

**5 points**: The notebook turns the broad question into one a computer can answer, and says how.

  - It states which documents are included and why, and how you checked that nothing important
    was left out.
  - It says what counts as an answer. For example, it explains what separates an agency finding
    that climate change threatens a species from a passing mention of climate change, with real
    examples from the text.
  - Where a different reasonable choice would change the answer, the notebook says so.

## 2. Analysis and tool choice (**5 points**)

**5 points**: The analysis answers the question the notebook defined, using tools that fit each
step.

  - The notebook says which tool was used for each step and why it was a good fit.
  - Claims about speed, cost or accuracy are supported by measurements from this work.
  - Code is concise and readable, with each cell doing one clear task and markdown explaining the
    logic. The notebook runs from top to bottom within the memory of a student session.

## 3. Checking the models (**5 points**)

**5 points**: The student can answer the question _how do I know these results are right?_

  - Model outputs (classifications, retrieved passages, generated answers, extracted records) are
    compared against the source text, not taken on trust.
  - The notebook documents specific cases where you disagreed with a model, read the source, and
    decided who was right. It explains what each disagreement says about the tool.
  - At least one result is compared against an independent source, such as Delach et al. (2019).
    Before any difference is explained, the notebook establishes what each source counts.
  - The notebook is honest about who made each judgment. Labels or reflections produced by a
    model are described as such, and your own reading is described as yours.

## 4. Results (**3 points**)

**3 points**: The notebook gives a clear answer to the question, including how it has changed
since the 1990s. The answer is supported by a well-labeled figure or table, and the text says what
it shows and how much confidence it deserves.

## 5. Narrative and context (**6 points**)

**6 points**: The notebook tells a clear story that a reader outside the class could follow.

  - It explains the ecological stakes: which species are at risk from climate change, and why
    the way an agency describes that risk matters for their protection.
  - It explains the legal setting: what a listing decision is, and how the Endangered Species Act
    asks the agency to weigh threats.
  - Instructor headings are replaced with topical headings, and the text connects the code and
    figures to the argument.
  - It ends with a conclusion in your own words: what you found, how confident you are in it, and
    what you would do next.

## 6. Process and GitHub (**4 points**)

**4 points**:

  - The repository includes your conversations with your coding agent (in Kilo Code, use the
    task's export button and save the files in `prompts/`). These show the guidance you gave the
    agent, including definitions, corrections, and times you redirected it.
  - The README is updated with authorship information, a GitHub Actions badge with a correct link
    to the repository, and a description of what you found.
  - The repository passes the notebook check on GitHub Actions.
  - Commits show how the work developed, with clear messages.

## Failure conditions

The notebook fabricates data, or presents made-up or "example" numbers, quotations or citations
as if they came from the sources. (Automatic fail)

This applies without change to output from a language model. Models sometimes produce plausible
quotations or numbers that are not in the documents. Passing those along as real is the same
failure whether you typed them or accepted them.

The notebook presents a model's judgment as your own: for example, labels or reflections written
by a model and described as your reading. Using a model for these is allowed. Misrepresenting who
made the judgment is not.
