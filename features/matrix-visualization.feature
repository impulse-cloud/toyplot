Feature: Matrix visualization
    Scenario Outline: Matrix visualization
        Given a matrix
        And a matrix visualization <scenario>
        Then the visualization should match the <reference> reference image

        Examples:
            | scenario | reference |
            | created with the convenience API | matrix-default |
            | created with the standard API | matrix-default |
            | created with a custom palette | matrix-custom-palette |
            | created with a custom colormap | matrix-custom-colormap |
            | created with custom labels | matrix-custom-labels |
            | created with right and bottom index locators | matrix-right-bottom-locators |
