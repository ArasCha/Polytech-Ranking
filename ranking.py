import requests
from bs4 import BeautifulSoup
import re
import math


class Assessment:

    def __init__(self, _id: int, _my_mark: float):
        
        self.id = _id # necessary in order to find an assessment
        self.my_mark = _my_mark # the mark I got for this assessment
        self.all_marks: list[float] = [] # list of all marks of students of the assessment
        self.my_rank: int # my rank for this assessment
        self.my_rank_normalized: float # rank normalized (my_rank/number of students in the assessment)
        self.my_best_rank: int # rank if I would be ranked first between all the dudes who have the same grade

class Course:

    nb_students: int # Overall number of students
    class_rank: int # My overall rank

    def __init__(self, _name: str):

        self.name = _name # name of the course
        self.assessments: list[Assessment] = [] # assessments of the course


# ------------------------------------------------------------------------------------------------------------------

def get_data() -> BeautifulSoup:
    """
    Gets data from the GestNote

    Returns HTML structure
    """

    url = "https://scolarite.polytech.univ-nantes.fr"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "fr,fr-FR;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "max-age=0",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "upgrade-insecure-requests": "1",
        "cookie": "scolarite=r9au4jrdl7iqgikb5bqojpqto2"
    }

    import urllib3
    urllib3.disable_warnings()

    req = requests.get(url, headers=headers, verify=False)
    page = BeautifulSoup(req.text, 'html.parser')
    
    return page


def get_courses() -> list[Course]:
    """
    Gets all the assessments for each course
    """

    page = get_data()
    courses: list[Course] = []

    my_marks = page.find("div", {'class':"selectionMatiereUEMin"})
    
    tables = my_marks.find_all("table")
    tables.pop(len(tables)-1) # on supprime le bloc de la moyenne générale

    for table in tables:
        
        ue_courses: list = table.find_all("tr")
        ue_courses.pop(0)
        ue_courses.pop(len(ue_courses)-1)
        ue_courses.pop(len(ue_courses)-1)
        
        for ue_course in ue_courses:
            name = ue_course.find("span", {"id": re.compile(r'mat')})
            marks = ue_course.find_all("div", {"id": re.compile(r'note')})

            course = Course(name.text)
            courses.append(course)
            
            for mark in marks:
                mark_value = mark.text
                mark_id = mark.get("id")

                try: # assessments that don't have any mark are skipped
                    assessment = Assessment(mark_id, float(mark_value))
                    course.assessments.append(assessment)
                except ValueError: pass

    build_all_marks(page, courses)

    courses_filtered = filter_courses_where_we_all_have_the_same_mark(courses)

    return courses_filtered


def filter_courses_where_we_all_have_the_same_mark(courses: list[Course]):

    for course in courses:
        course.assessments = [ass for ass in course.assessments if not all(mark == ass.all_marks[0] for mark in ass.all_marks)]

    return courses


def build_all_marks(page: BeautifulSoup, courses: list[Course]) -> None:
    """
    Retrieves all marks of each assessment of all courses
    """

    scripts = page.find_all("script")
    all_marks_script = scripts[-1]

    result = re.search("('(.*)')", str(all_marks_script))
    html_text = result.group(1)

    html = BeautifulSoup(html_text, 'html.parser')

    for course in courses: # builds the list of tags that have a mark
        for assessment in course.assessments:
            
            tag = html.find(key=assessment.id)

            result = re.search('(\[(.*)\])', str(tag["exec"])) # "\" to search "[" and "]"
            b = result.group(1)
            a = b.strip('[]')
            marks = [float(mark) for mark in a.split(",")]
            
            assessment.all_marks = marks


def build_my_ranks(courses: list[Course], pessimistic: bool) -> None:
    """
    Calculates all my ranks in each assessment
    """
    for course in courses:
        for assessment in course.assessments:

            assessment.all_marks.sort(reverse=True)
            rank_not_averaged = assessment.all_marks.index(assessment.my_mark) + 1
            assessment.my_best_rank = rank_not_averaged

            raw_ranks = [i+1 for i in range(len(assessment.all_marks))]
            averaged_ranks = agg_mean(assessment.all_marks, raw_ranks)
            
            rank_averaged = averaged_ranks[rank_not_averaged - 1]

            if pessimistic:
                rank_averaged_int = int(math.ceil(averaged_ranks[rank_not_averaged - 1]))
            else:
                rank_averaged_int = int(averaged_ranks[rank_not_averaged - 1])

            assessment.my_rank = rank_averaged_int
            assessment.my_rank_normalized = rank_averaged/len(assessment.all_marks)
    
    Course.class_rank = get_class_rank(courses, pessimistic)


def display(courses: list[Course]) -> None:

    for course in courses:

        print(course.name)
        for assessment in course.assessments:
            print(f"Note: {assessment.my_mark}/20")
            print(f"Rang: {assessment.my_rank}/{len(assessment.all_marks)}")
            # print(f"Meilleur Rang: {assessment.my_best_rank}/{len(assessment.all_marks)}")

        print("\n")
    print(f"Rang dans la classe estimé: {Course.class_rank}/{Course.nb_students}")


def agg_mean(col: list = [1, 7, 1, 10, 5, 10, 8, 9, 10], col_to_agg: list = [1, 3, 2, 7, 4, 8, 5, 6, 9]) -> list[float]:
    """
    1st argument: list of marks (sorted or not)
    2nd argument: list of ranks (all its values must be different)
    The 2 lists must be arranged together: a note in index i of the list
    of notes must have its corresponding rank in index i of the list of ranks
    @Example:
    >>> agg_mean([1, 7, 1, 10, 5, 10, 8, 9, 10], [1, 3, 2, 7, 4, 8, 5, 6, 9])
    @Returns:
    >>> [1.5, 3.0, 1.5, 8.0, 4.0, 8.0, 5.0, 6.0, 8.0]
    """
    assert len(col) == len(col_to_agg)
    same_value_indexes = []
    for elt in col:
        same_value_indexes.append([i for i in range(len(col)) if col[i]==elt])

    assert len(same_value_indexes) == len(col_to_agg)

    averaged_col = []
    for index_list in same_value_indexes:
        data_to_mean = [col_to_agg[i] for i in range(len(col_to_agg)) if i in index_list]
        mean = sum(data_to_mean)/len(index_list)
        averaged_col.append(mean)

    return averaged_col


def get_class_rank(courses: list[Course], pessimistic: bool):
    """
    Returns my overall rank
    """

    all_my_normalized_ranks = []
    numbers_of_students = [] # nb of students for each assessment
    for course in courses: 
        [all_my_normalized_ranks.append(ass.my_rank_normalized) for ass in course.assessments]
        [numbers_of_students.append(len(ass.all_marks)) for ass in course.assessments]

    Course.nb_students = max(numbers_of_students)

    mean_normalized = sum(all_my_normalized_ranks)/len(all_my_normalized_ranks)

    rank_mean = mean_normalized * Course.nb_students

    if pessimistic:
        return int(math.ceil(rank_mean))
    return int(rank_mean)


if __name__ == "__main__":

    courses = get_courses()
    build_my_ranks(courses, pessimistic=False)
    
    display(courses)
