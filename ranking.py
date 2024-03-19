import requests
from bs4 import BeautifulSoup
import re


class Ranking:

    def __init__(self, all_marks: list[float], mark: float) -> None:
        self.all_marks = sorted(all_marks, reverse=True)
        self.mark = mark
        self.mean_rank: int
        self.best_rank: int # rank if I would be ranked first among all the dudes who have the same grade
        self.worst_rank: int # rank if I would be ranked last among all the dudes who have the same grade
        self.normalized_best_rank = self.calculate_normalized_best_rank()
        self.normalized_mean_rank = self.calculate_normalized_mean_rank()
        self.normalized_worst_rank = self.calculate_normalized_worst_rank()
        # The normalized one are meant to be used to calculate the general mean/best/worst rank

    @staticmethod
    def aggregate_by_mean(col: list[float], col_to_agg: list[int]) -> list[float]:
        """
        Put the same averaged rank to dudes which have the same mark

        1st argument: list of marks (sorted or not)
        2nd argument: list of ranks (all its values must be different)
        The 2 lists must be arranged together: a note in index i of the list
        of notes must have its corresponding rank in index i of the list of ranks
        @Example:
        >>> aggregate_by_mean([1, 7, 1, 10, 5, 10, 8, 9, 10], [1, 3, 2, 7, 4, 8, 5, 6, 9])
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

    def calculate_normalized_best_rank(self) -> float:
        self.best_rank = self.all_marks.index(self.mark) + 1
        return self.best_rank/len(self.all_marks)

    def calculate_normalized_mean_rank(self) -> float:

        raw_ranks = [i+1 for i in range(len(self.all_marks))]
        averaged_ranks = Ranking.aggregate_by_mean(self.all_marks, raw_ranks)
        
        my_rank_averaged = averaged_ranks[self.best_rank - 1]
        self.mean_rank = int(round(my_rank_averaged))

        return my_rank_averaged/len(self.all_marks)

    def calculate_normalized_worst_rank(self) -> float: # need to be normalized

        ascending_order_marks = list(reversed(self.all_marks))
        index = ascending_order_marks.index(self.mark)
        self.worst_rank = len(self.all_marks) - index
        return self.worst_rank/len(self.all_marks)


class Assessment:

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.all_marks = self.get_all_marks() # list of all marks of students of the assessment
        self.my_mark: float # the mark I got for this assessment
        self.ranking = Ranking(self.all_marks, self.my_mark)

    def get_all_marks(self) -> list[float]:

        marks_data = Semester.all_marks_data
        all_marks_tag = next((tag for tag in marks_data if tag["key"] == self.id), None) # selects the relevant tag
        str_to_parse = str(all_marks_tag)

        mark_search_string = re.search('.setnote\((.*)\)', str_to_parse).group(1)
        mark_string = mark_search_string.strip('()')
        self.my_mark = float(mark_string)

        marks_search_string = re.search('(\[(.*)\])', str_to_parse).group(1) # searches string between "([" and "])"
        marks_string_data = marks_search_string.strip('[]')

        return [float(mark) for mark in marks_string_data.split(",")]


class Course:

    def __init__(self, data: BeautifulSoup):
        self.data = data
        self.id: str = self.init_id()
        self.name: str = self.init_name()
        self.weight = self.init_weight()
        self.assessments: list[Assessment] = self.init_assessments()

    def init_id(self) -> str:
        return self.data.find("span", id = re.compile(r'mat'))["id"]

    def init_name(self) -> str:
        return self.data.find("span", id = re.compile(r'mat')).text

    def init_weight(self) -> float:

        weight_tags: list[BeautifulSoup] = self.data.find_all("div")
        weight_tag = next((tag for tag in weight_tags if "coef" in tag.text), None)

        text_to_parse = weight_tag.text
        weight = re.search(r'\b\d+\.?\d*\b', text_to_parse).group(0)
        return float(weight)

    def init_assessments(self) -> list[Assessment]:
        
        mark_tags: list[BeautifulSoup] = self.data.find_all("div", id = re.compile(r'note'))
        [mark_tags.remove(tag) for tag in mark_tags if tag.text == "-"]

        asses = []
        for mark_tag in mark_tags:
            assessment_name_tag = mark_tag.find_parent().next_sibling
            asses.append(Assessment(id=mark_tag["id"], name=assessment_name_tag.text))
            # We don't specify the mark here although we could because some teachers
            # put a coma instead of a point for float numbers. We'll get it from the graph data

        [asses.remove(ass) for ass in asses if all(mark == ass.all_marks[0] for mark in ass.all_marks)]
        # deletes assessments where we all have the same mark 'cause useless to calculate ranks

        return asses    


class UE:

    def __init__(self, data: BeautifulSoup) -> None:
        self.data = data
        self.id: str = self.init_id()
        self.name: str = self.init_name()
        self.courses: list[Course] = self.init_courses()
        self.rank: int

    def init_id(self) -> str:
        return self.data.find("span", id = re.compile(r'ue'))["id"]

    def init_name(self) -> str:
        return self.data.find("span", id = re.compile(r'ue')).text

    def init_courses(self) -> list[Course]:
        
        courses_tags = self.data.find_all("tr")
        courses_tags[:] = [tag for tag in courses_tags
            if tag.find("span").has_attr("id") # removes style spans
            and "_0" not in tag.find("span").get("id") # removes "Bonification nanana ..."
            and "mat" in tag.find("span").get("id") # removes UEs names tags
        ]

        return [Course(data=tag) for tag in courses_tags]


class Semester:

    all_marks_data: list[BeautifulSoup]

    def __init__(self, number: int, cookie: str) -> None:

        assert number >= 1, "Le numéro de semestre doit être supérieur ou égal à 1"
        assert number <= 10 , "Le numéro de semestre doit être inférieur ou égal à 10"

        self.number = number
        self.data: BeautifulSoup = self.get_data(cookie)
        self.UEs: list[UE] = self.init_UEs()
        self.nb_students = self.calculate_nb_students()

    def init_UEs(self) -> list[UE]:

        UEs_tags = self.data.find_all("div", class_ = "OrgaUERecap")

        UEs_tags[:] = [tag for tag in UEs_tags
            if tag.find("span", id = re.compile(r'ue')) # keeps tags which have "ue..." as id
            and tag.find("span", id = re.compile(r'ue')).has_attr("id") # and have an "id" attribute
        ]

        return [UE(data = tag) for tag in UEs_tags]

    def get_data(self, cookie: str) -> BeautifulSoup:
        """
        Gets data from the GestNote

        Returns HTML structure
        """

        semesters = { 5: 395, 6: 396, 7: 458, 8: 462, 9: 535, 10: 536 }

        url = f"https://scolarite.polytech.univ-nantes.fr/gestnote/?fct=bulletin&maq={semesters[self.number]}&dpt=1"
        headers = {
            "accept": "*/*",
            "accept-language": "fr,fr-FR;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Microsoft Edge\";v=\"109\", \"Chromium\";v=\"109\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "cookie": f"logged_out_marketing_header_id=; scolarite={cookie}",
            "Referer": "https://scolarite.polytech.univ-nantes.fr/",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    
        import urllib3
        urllib3.disable_warnings()

        req = requests.get(url, headers=headers, verify=False)

        import html
        page = BeautifulSoup(html.unescape(req.text), "html.parser")
        
        assert not page.find("title"), "Renseigne les bonnes valeurs de cookie ou le bon numéro de semestre"

        Semester.all_marks_data = page.find_all("addhelp", key = re.compile(r'note'))

        return page

    def calculate_nb_students(self) -> int:
        """
        Number of students of the promo
        """
        numbers_of_students = [] # nb of students for each assessment
        for course in [course for ue in self.UEs for course in ue.courses]:
            [numbers_of_students.append(len(ass.all_marks)) for ass in course.assessments]

        return max(numbers_of_students)
    
    def rank(self, type: str) -> int:
        """
        Overall rank for the semester
        """
        assert type in ["mean", "best", "worst"]

        all_my_normalized_ranks_weighted = []
        courses_weights = []

        for course in [course for ue in self.UEs for course in ue.courses]:
            for ass in course.assessments:
                normalized_rank_weighted = getattr(ass.ranking, f"normalized_{type}_rank")*course.weight
                all_my_normalized_ranks_weighted.append(normalized_rank_weighted)
            
            courses_weights.append(course.weight)
            
        averaged_normalized_rank = sum(all_my_normalized_ranks_weighted)/sum(courses_weights)

        return int(round(averaged_normalized_rank * self.nb_students))

    def __str__(self):
        
        print(f"Semestre {self.number}\n")

        for course in [course for ue in self.UEs for course in ue.courses]:
            print(course.name)

            for ass in course.assessments:
                print(f"{ass.name}: ")
                print(f"    Note: {ass.my_mark}/20")
                print(f"    Rang: {ass.ranking.mean_rank}/{len(ass.all_marks)} - Au mieux: {ass.ranking.best_rank} - Au pire: {ass.ranking.worst_rank}")

            print("\n")
        return f"Rang dans la classe estimé: {self.rank('mean')}/{self.nb_students} - Au mieux: {self.rank('best')} - Au pire: {self.rank('worst')}"
    
# ------------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    
    with open("params.json", "r") as f:
        content_str = f.read()
        import json
        content_json = json.loads(content_str)
        
    data = Semester(number=content_json["semester"], cookie=content_json["scolarite"])

    print(data)
