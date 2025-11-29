from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
import logging
import unicodedata

from enum import IntEnum

import re


class Weekday(IntEnum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6

@dataclass
class DictData:
    data: dict
    # Used to convert dicts to Dataclasses
    # Eg. dd = DictData({'a':22, 'b':'Hello'})
    # print(dd.a, dd.b)
    def __post_init__(self):
        for key, value in self.data.items():
            setattr(self, key, value)

@dataclass
class ValueWrapper:
    value:object

    def __eq__(self, other):
        if not isinstance(other, ValueWrapper):
            return NotImplemented
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

# Requirements using Decorator Pattern

class BaseRequirement:
    def __init__(self):
        pass

    def match(self, opportunity):
        return (self._match_requirement(opportunity) and self.wrapped_obj.match(opportunity)) if self.wrapped_obj else self._match_requirement(opportunity)

    def __eq__(self, other):
        if not isinstance(other, BaseRequirement):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self):
        # Convert internal dict to tuple of sorted items for consistent hashing
        return hash(tuple(sorted(self.__dict__.items())))

    def __str__(self):
        #return f"BaseRequirement"
        return f"BaseRequirement:  {self.wrapped_obj if self.wrapped_obj else ''}"

class WithinRequirement(BaseRequirement):
    def __init__(self, within, wrapped_obj=None):
        self.within = within
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        #due_to_start =int((datetime.fromisoformat(opportunity.start) - datetime.now(timezone.utc)).total_seconds()//60),
        logging.info(f"match_requirement: WithinRequirement {self.within} against {opportunity.due_to_start}")
        return opportunity.due_to_start <= self.within

    def __eq__(self, other):
        if not isinstance(other, WithinRequirement):
            return NotImplemented
        return self.within == other.within and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.within, self.wrapped_obj))

    def __str__(self):
        return f"WithinRequirement: {self.within} {self.wrapped_obj if self.wrapped_obj else ''}"
  
class NoticeRequirement(BaseRequirement):
    def __init__(self, minnotice, wrapped_obj=None):
        self.minnotice = minnotice
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        #due_to_start =int((datetime.fromisoformat(opportunity.start) - datetime.now(timezone.utc)).total_seconds()//60),
        logging.info(f"match_requirement: NoticeRequirement {self.minnotice} against {opportunity.due_to_start} MATCH = {opportunity.due_to_start >= self.minnotice}")
        return opportunity.due_to_start >= self.minnotice

    def __eq__(self, other):
        if not isinstance(other, NoticeRequirement):
            return NotImplemented
        return self.minnotice == other.minnotice and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.minnotice, self.wrapped_obj))

    def __str__(self):
        return f"NoticeRequirement: {self.minnotice} {self.wrapped_obj if self.wrapped_obj else ''}"
   

class PeriodRequirement(BaseRequirement): # Requirement between two dates
    def __init__(self, from_date, to_date, wrapped_obj=None):
        self.from_date = from_date
        self.to_date = to_date
        self.wrapped_obj = wrapped_obj

    def _is_between_dates(self, date_str, start_date_str, end_date_str):
        date = datetime.strptime(date_str, '%Y-%m-%d')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        return start_date <= date <= end_date

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: PeriodRequirement: {self} against {opportunity} MATCH = {self._is_between_dates(opportunity.date, self.from_date, self.to_date)}")
        return self._is_between_dates(opportunity.date, self.from_date, self.to_date)

    def __eq__(self, other):
        if not isinstance(other, PeriodRequirement):
            return NotImplemented
        return self.from_date == other.from_date and self.to_date  == other.to_date and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.from_date, self.to_date, self.wrapped_obj))

    def __str__(self):
        return f"PeriodRequirement: {self.from_date} to {self.to_date} {self.wrapped_obj if self.wrapped_obj else ''}"

class ExcludePeriodRequirement(BaseRequirement): # Requirement between two dates

    def __init__(self, from_date, to_date, wrapped_obj=None):
        self.from_date = from_date
        self.to_date = to_date
        self.wrapped_obj = wrapped_obj

    def _is_between_dates(self, date_str, start_date_str, end_date_str):
        date = datetime.strptime(date_str, '%Y-%m-%d')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        return start_date <= date <= end_date

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: ExcludePeriodRequirement: {self} against {opportunity}")
        return not self._is_between_dates(opportunity.date, self.from_date, self.to_date)

    def __eq__(self, other):
        if not isinstance(other, ExcludePeriodRequirement):
            return NotImplemented
        return self.from_date == other.from_date and self.to_date  == other.to_date and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.from_date, self.to_date, self.wrapped_obj))

    def __str__(self):
        return f"ExcludePeriodRequirement: {self.from_date} to {self.to_date} {self.wrapped_obj if self.wrapped_obj else ''}"

class DateRequirement(BaseRequirement):
    def __init__(self, claim_date, wrapped_obj=None):
        self.claim_date = claim_date if isinstance(claim_date, str) else str(claim_date)
        self.wrapped_obj = wrapped_obj


    # Match a given opportunity date with claim_date
    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: DateRequirement: {self} against {opportunity} DATE COMPARE: '{self.claim_date}' v '{opportunity.date}'")
        return opportunity.date == self.claim_date


    def __eq__(self, other):
        if not isinstance(other, DateRequirement):
            return NotImplemented
        return self.claim_date == other.claim_date and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.claim_date, self.wrapped_obj))

    def __str__(self):
        return f"DateRequirement: {self.claim_date} {self.wrapped_obj if self.wrapped_obj else ''}"

class SkillRequirement(BaseRequirement):
    def __init__(self, reqskill, wrapped_obj=None):
        self.reqskill = reqskill
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: SkillRequirement required '{self.reqskill}' against '{opportunity.skill}'")
        return self.reqskill.lower() in opportunity.skill.lower()

    def __eq__(self, other):
        if not isinstance(other, SkillRequirement):
            return NotImplemented
        return self.reqskill == other.reqskill and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.reqskill, self.wrapped_obj))

    def __str__(self):
        return f"SkillRequirement: {self.reqskill} {self.wrapped_obj if self.wrapped_obj else ''}"


class TypeRequirement(BaseRequirement):

    def __init__(self, reqtype, wrapped_obj=None):
        self.reqtype = reqtype
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: TypeRequirement: {self.reqtype} against {opportunity.type} MATCH={self.reqtype in opportunity.type}")
        return self.reqtype in opportunity.type

    def __eq__(self, other):
        if not isinstance(other, TypeRequirement):
            return NotImplemented
        return self.reqtype == other.reqtype and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.reqtype, self.wrapped_obj))

    def __str__(self):
        return f"TypeRequirement: {self.reqtype} {self.wrapped_obj if self.wrapped_obj else ''}"

class MaxTimeRequirement(BaseRequirement):
    def __init__(self, maxtime, wrapped_obj=None):
        self.maxtime = maxtime
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: MaxTimeRequirement {self.maxtime} MATCH={opportunity.duration <= self.maxtime}")
        return opportunity.duration <= self.maxtime

    def __eq__(self, other):
        if not isinstance(other, MaxTimeRequirement):
            return NotImplemented
        return self.maxtime == other.maxtime and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.maxtime, self.wrapped_obj))

    def __str__(self):
        return f"MaxTimeRequirement: {self.maxtime} {self.wrapped_obj if self.wrapped_obj else ''}"

class StartTimeRequirement(BaseRequirement):
    def __init__(self, starttime_pattern, wrapped_obj=None):
        self.starttime_pattern = starttime_pattern
        self.wrapped_obj = wrapped_obj

    def match_time_pattern(self, time_str: str, pattern: str) -> bool:
        """
        Matches a time string ('HH:MM[:SS]') against a simplified pattern.
        - Ignores leading/trailing whitespace
        - '*' matches a single digit (0–9)
        - '[x-y]' is treated as a normal regex character class
        - Ignores any ':SS' seconds part in time_str

        - ':' is a literal
        """
        time_str = time_str.strip()

        # Strip seconds if present
        time_hhmm = time_str[:5] if len(time_str) >= 5 else time_str

        # Convert simplified pattern to regex
        regex_pattern = pattern.replace('*', '[0-9]')
    
        # Anchor the regex
        regex_pattern = f'^{regex_pattern}$'
    
        return re.match(regex_pattern, time_hhmm) is not None

    def _match_requirement(self, opportunity) -> bool:
        logging.info(f"match_requirement: StartTimeRequirement {self.starttime_pattern} Vs {opportunity.start} MATCH={self.match_time_pattern(opportunity.start, self.starttime_pattern)}")
        return self.match_time_pattern(opportunity.start, self.starttime_pattern)

    def __eq__(self, other):
        if not isinstance(other, StartTimeRequirement):
            return NotImplemented
        return self.starttime_pattern == other.starttime_pattern and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.starttime_pattern, self.wrapped_obj))

    def __str__(self):
        return f"StartTimeRequirement: {self.starttime_pattern} {self.wrapped_obj if self.wrapped_obj else ''}"

class MinTimeRequirement(BaseRequirement):
    def __init__(self, mintime, wrapped_obj=None):
        self.mintime = mintime
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: MinTimeRequirement {self.mintime} MATCH={opportunity.duration >= self.mintime}")
        return opportunity.duration >= self.mintime

    def __eq__(self, other):
        if not isinstance(other, MinTimeRequirement):
            return NotImplemented
        return self.mintime == other.mintime and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.mintime, self.wrapped_obj))

    def __str__(self):
        return f"MinTimeRequirement: {self.mintime} {self.wrapped_obj if self.wrapped_obj else ''}"

class ExactTimeRequirement(BaseRequirement):
    def __init__(self, exacttime, wrapped_obj=None):
        self.exacttime = exacttime
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: ExactTimeRequirement {self.exacttime}")
        return opportunity.duration == self.exacttime

    def __eq__(self, other):
        if not isinstance(other, ExactTimeRequirement):
            return NotImplemented
        return self.exacttime == other.exacttime and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.exacttime, self.wrapped_obj))

    def __str__(self):
        return f"ExactTimeRequirement: {self.exacttime} {self.wrapped_obj if self.wrapped_obj else ''}"

class DayRequirement(BaseRequirement):
    def __init__(self, daymask, wrapped_obj=None):
        self.daymask = daymask if isinstance(daymask, int) else self._string_to_mask(daymask)
        self.wrapped_obj = wrapped_obj

    # Convert strings like 'sunday, monday, tuesday' to an integer bitmask
    def _string_to_mask(self, strv):
        daybits = {
            'sun':0,
            'mon':1,
            'tue':2,
            'wed':3,
            'thu':4,
            'fri':5,
            'sat':6,
        }
        #ustr = ','.join(set(strv.lower().split(',')))
        mask = sum({1<<daybits[d] for d in daybits if d in strv.lower()})
        return mask

    def _match_requirement(self, opportunity):
        jsday_of_week = ((datetime.strptime(opportunity.date,"%Y-%m-%d").weekday() + 1) % 7)
        logging.info(f"match requirement: DayRequirement {opportunity.date} day mask {1<<jsday_of_week} wanted mask = {self.daymask} MATCH = {((1<<jsday_of_week) & self.daymask) != 0}")
        return ((1<<jsday_of_week) & self.daymask) != 0

    def __eq__(self, other):
        if not isinstance(other, DayRequirement):
            return NotImplemented
        return self.daymask == other.daymask and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.daymask, self.wrapped_obj))

      
    def __str__(self):
        return f"DayRequirement: {self.daymask} {self.wrapped_obj if self.wrapped_obj else ''}"

class IDRequirement(BaseRequirement):
    def __init__(self, id, wrapped_obj=None):
        self.id = id
        self.wrapped_obj = wrapped_obj

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: IDRequirement: {self.id} {type(self.id)}")
        return self.id in opportunity.id

    def __eq__(self, other):
        if not isinstance(other, IDRequirement):
            return NotImplemented
        return self.id == other.id and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.id, self.wrapped_obj))

    def __str__(self):
        return f"IDRequirement: {self.id} {self.wrapped_obj if self.wrapped_obj else ''}"

class BooleanRequirement(BaseRequirement):
    def __init__(self, bol, wrapped_obj=None):
        self.bol = bol
        self.wrapped_obj = wrapped_obj

    def getValueWrapper(self):
        return self.bol if not isinstance(self.bol,bool) else None

    def _match_requirement(self, opportunity):
        logging.info(f"match_requirement: BooleanRequirement({type(self.bol)}): MATCH = {self.bol if isinstance(self.bol,bool) else self.bol.value} {type(self.bol)}")    
        return self.bol if isinstance(self.bol,bool) else (self.bol.value != 0)

    def __eq__(self, other):
        if not isinstance(other, BooleanRequirement):
            return NotImplemented
        return self.bol == other.bol and self.wrapped_obj == other.wrapped_obj

    def __hash__(self):
        return hash((self.bol, self.wrapped_obj))

    def __str__(self):
        return f"BooleanRequirement: {self.bol} Type: {type(self.bol)} {self.wrapped_obj if self.wrapped_obj else ''}"

@dataclass
class Opportunity:
    data: dict

    def __post_init__(self):
        #for key, value in self.data.items():
        #    setattr(self, key, value)
        for key,value in sorted(self.data.items()):
            normvalue = unicodedata.normalize('NFC', value) if isinstance(value,str) else value 
            setattr(self, key, normvalue if not isinstance(value,list) else tuple(sorted(value)))
            #setattr(self, key, value)



    def __str__(self):
        items = [f"{key}: {value}" for key, value in self.data.items()]
        return f"Opportunity: {{ {', '.join(items)} }}"

#from datetime import datetime, timedelta

# Based on Working Week starting on Sunday and ending on Saturday - 6 days later
def get_working_week_dates(input_date):
    # Convert input_date to datetime object
    input_datetime = datetime.strptime(input_date, '%Y-%m-%d')
    sunday_week_offset = (input_datetime.weekday() + 1) % 7

    # Find the Sunday of the input week
    sunday_of_week = input_datetime - timedelta(days=sunday_week_offset)

    # Find the Saturday of the input week
    saturday_of_week = sunday_of_week + timedelta(days=6)

    # Format the dates as strings in 'YYYY-MM-DD' format
    sunday_str = sunday_of_week.strftime('%Y-%m-%d')
    saturday_str = saturday_of_week.strftime('%Y-%m-%d')

    return sunday_str, saturday_str

def build_working_datetime_from(date:str, offset:int) -> str:
    working_week = get_working_week_dates(date)
    start_datetime = datetime.strptime(working_week[0], '%Y-%m-%d')
    work_date = start_datetime + timedelta(offset)
    return work_date.strftime('%Y-%m-%d')


class RequirementsManager():

    def __init__(self):
        self.clearRequirements()

    def clearRequirements(self):
        self.requirements = set()
        self.constantVTORequirement = DayRequirement(0, 'TIME_OFF')

    def setRequirements(self, requirements):
        self.requirements = requirements

    def setConstantVTORequirement(self, requirement):
        self.constantVTORequirement = requirement

    def getConstantVTORequirement(self):
        return self.constantVTORequirement 

    def addRequirements(self, requirement:BaseRequirement):
        if (requirement in self.requirements):
            logging.info(f"addRequirements: ignore adding - {requirement} - as this already exists!")
        else:
            self.requirements.add(requirement)
            logging.info(f"Added Requirement {requirement}")

    def addClaim(self, requirement:BaseRequirement):
        self.addRequirements(requirement)

    def removeOneOffClaims(self):
        self.requirements = set([_ for _ in list(self.requirements) if not isinstance(_, IDRequirement)])
        logging.info(f"Removing redundant one off (IDRequirement) claims {self}")

    
    def removeOneOffIDClaimsThatMatch(self, id_opportunity_list):
        """
        Remove any IDRequirement whose 'id' match in the list 'matched'
        'matched' is a list of string tuples (id, type) 
        """
        logging.info(f"removeOneOffIDClaimsThatMatch(): {id_opportunity_list}")
        # Extract the set of IDs from the tuple list
        ids_to_remove = {id_ for id_, _ in id_opportunity_list}

        # Filter the requirements set, keeping only those that do not match IDRequirement with the given IDs
        self.requirements = {
            req for req in self.requirements
            if not (isinstance(req, IDRequirement) and req.id in ids_to_remove)
        }

        logging.info(f"Removed redundant one off claims (IDRequirement) from our last attempt {ids_to_remove}")
        logging.info(f"New RequirementManager: {self}")

    def find_type_requirement(self, root, target_type):
        """
        Traverse a BaseRequirement decorator chain to check for a TypeRequirement with a specific type.
    
        :param root: BaseRequirement or subclass (root of the chain)
        :param target_type: str, e.g., 'EXTRA_TIME'
        :return: TypeRequirement instance if found, else None
        """
        current = root
        while isinstance(current, BaseRequirement):
            if isinstance(current, TypeRequirement) and getattr(current, 'reqtype', None) == target_type:
                return current
            current = getattr(current, 'wrapped_obj', None)
        return None

    def removeTypeRequirements(self, t_type):
        newlist = [_ for _ in list(self.requirements) if not self.find_type_requirement(_, t_type)]
        self.requirements = set(newlist)

    def clearVETrequirements(self):
        self.removeTypeRequirements('EXTRA_TIME')

    def clearVTOrequirements(self):
        self.removeTypeRequirements('TIME_OFF')

    def hasClaims(self):
        return any([_ for _ in list(self.requirements) if  isinstance(_, IDRequirement)])

    def getRequirements(self):
        return [self.constantVTORequirement] + list(self.requirements)

    def extract_matched_opportunties(self, all_opportunities):
        matched_opportunities = [(opportunity.id, opportunity.type) for opportunity in all_opportunities if any(_.match(opportunity) for _ in self.getRequirements())]
        return matched_opportunities

    def __str__(self):
        requirements_str = '[' + ', '.join(str(requirement) for requirement in self.getRequirements()) + ']'
        return "RequirementsManager:" + requirements_str + f" size: {len(self.getRequirements())}" 


if __name__ == '__main__':

    import unittest

    def test(quit_on_error = True):

        tests_success = 0
        tests_failed = 0
        tested = 0

        manager = RequirementsManager()

        def show_requirements(title:str):
            logging.info(f"{title}")
            for index,req in enumerate(manager.getRequirements()):
                logging.info(f"{index}, {req}")


        def assert_test(cond, test_name):
            nonlocal tests_success, tests_failed, tested
            tested = tested + 1

            try:
                assert cond, "**FAILED**" 
                print(f"{test_name} PASSED")
                tests_success  = tests_success + 1

            except AssertionError as e:
                print(f"{test_name} {e}")
                tests_failed  = tests_failed + 1
                if (quit_on_error):
                    raise(Exception(f"{test_name} {e}"))

        today = date.today()

        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)

        # Calculate yesterday's date
        seven_days_from_now = today + timedelta(days=7)
        three_days_from_now = today + timedelta(days=3)
        four_days_from_now = today + timedelta(days=4)
        five_days_from_now = today + timedelta(days=5)
        six_days_from_now = today + timedelta(days=6)
        thirty_days_from_now = today + timedelta(days=30)

        # Build Dates (Strings) for the current working week (SUNDAY, MONDAY... SATURDAY)
        this_sunday = build_working_datetime_from(str(today), Weekday.SUNDAY)
        this_monday = build_working_datetime_from(str(today), Weekday.MONDAY)
        this_tuesday = build_working_datetime_from(str(today), Weekday.TUESDAY)
        this_wednesday = build_working_datetime_from(str(today), Weekday.WEDNESDAY)
        this_thursday = build_working_datetime_from(str(today), Weekday.THURSDAY)
        this_friday = build_working_datetime_from(str(today), Weekday.FRIDAY)
        this_saturday = build_working_datetime_from(str(today), Weekday.SATURDAY)


        today_opp = Opportunity({
                    'date': str(today),
            })

        tomorrow_opp = Opportunity({
                    'date': str(tomorrow),
            })
        next_week_opp = Opportunity({
                    'date': str(seven_days_from_now),
            })



        w1 = WithinRequirement(300)
        w2 = WithinRequirement(300)
        w3 = WithinRequirement(301)

        assert_test(w1 == w2,"Test 1")
        assert_test(w2 == w1,"Test 2")
        assert_test(w3 != w1,"Test 3")

        n1 = NoticeRequirement(300)
        n2 = NoticeRequirement(300)
        n3 = NoticeRequirement(301)

        assert_test(n1 == n2,"Test 4")
        assert_test(n2 == n1,"Test 5")
        assert_test(n3 != n1,"Test 6")


        p1 = PeriodRequirement(str(today), str(three_days_from_now))
        p2 = PeriodRequirement(str(today), str(three_days_from_now))
        p3 = PeriodRequirement(str(today), str(seven_days_from_now))

        assert_test(p1 == p2,"Test 7")
        assert_test(p2 == p1,"Test 8")
        assert_test(p3 != p1,"Test 9")

        e1 = ExcludePeriodRequirement(today, three_days_from_now)
        e2 = ExcludePeriodRequirement(today, three_days_from_now)
        e3 = ExcludePeriodRequirement(today, seven_days_from_now)

        assert_test(e1 == e2,"Test 10")
        assert_test(e2 == e1,"Test 11")
        assert_test(e3 != e1,"Test 12")

        d1 = DateRequirement(today)
        d2 = DateRequirement(today)
        d3 = DateRequirement(seven_days_from_now)

        assert_test(d1 == d2,"Test 13")
        assert_test(d2 == d1,"Test 14")
        assert_test(d3 != d1,"Test 15")

        period_requirement = PeriodRequirement(str(today), str(three_days_from_now))

        assert_test(period_requirement.match(today_opp), "Test 16")
        assert_test(period_requirement.match(tomorrow_opp), "Test 17")
        assert_test(not period_requirement.match(next_week_opp), "Test 18")


        opportunity = Opportunity({

            'date': str(today),
            'type': 'EXTRA_TIME',
            'duration': 240,
            'due_to_start' : 121,
            'id': 'SOME_UID'
        })

        opp_requirement = NoticeRequirement(270,
                          MinTimeRequirement(240,
                          MaxTimeRequirement(330,
                          TypeRequirement('EXTRA_TIME',
                          DayRequirement('monday, tuesday, wednesday, thursday, friday, saturday, sunday',
                          PeriodRequirement(str(today), str(thirty_days_from_now) ))))))

        assert_test(opp_requirement.match(Opportunity({
            'date': str(seven_days_from_now),
            'type': 'EXTRA_TIME',
            'duration': 240,
            'due_to_start' : 270,
            'id': 'SOME_UID'
        })), "Test 19")


        assert_test(not opp_requirement.match(Opportunity({
            'date': str(seven_days_from_now),
            'type': 'EXTRA_TIME',
            'duration': 60,
            'due_to_start' : 270,
            'id': 'SOME_UID'
        })), "Test 20")


        assert_test(not opp_requirement.match(Opportunity({
            'date': str(seven_days_from_now),
            'type': 'TIME_OFF',
            'duration': 60,
            'due_to_start' : 270,
            'id': 'SOME_UID'
        })), "Test 21")


        vto_requirement =    DayRequirement('saturday, sunday',
                             TypeRequirement('TIME_OFF'))

        vet_requirement =   NoticeRequirement(480,
                            PeriodRequirement(str(today), str(tomorrow),
                            DayRequirement('monday, tuesday, wednesday, thursday, friday, saturday, sunday',
                            TypeRequirement('EXTRA_TIME',
                            MinTimeRequirement(300,
                            MaxTimeRequirement(390)
                        )))))

        manager.setConstantVTORequirement(vto_requirement)

        all_ops = [
            Opportunity({
                    'date': str(tomorrow),
                    'id': 'SOME VET ID',
                    'duration': 300,
                    'due_to_start' : 500,
                    'type':'EXTRA_TIME'
            }),
            Opportunity({
                    'date': str(today),
                    'id': 'A SECOND VET ID',
                    'duration': 600,
                    'due_to_start' : 481,
                    'type':'EXTRA_TIME'
            }),
            Opportunity({
                    'date': str(this_monday),
                    'id': 'MONDAY VTO ID',
                    'duration': 60,
                    'due_to_start': 540,
                    'type':'TIME_OFF'
           }),
            Opportunity({
                    'date': str(this_sunday),
                    'id': 'SUNDAY VTO ID',
                    'duration': 10,
                    'due_to_start': 1,
                    'type':'TIME_OFF'
           }),
        ]    
        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == 1, "Test 22")
        manager.addRequirements(vet_requirement)
        manager.addRequirements(vet_requirement)


        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == 2, "Test 23")


        # Boolean
        boolwrapper = ValueWrapper(True)
        manager.clearRequirements()
        manager.addRequirements(BooleanRequirement(boolwrapper))
        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == len(all_ops), "Test 24")

        boolwrapper.value = False
        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == 0, "Test 25")
        # Additional Boolean
        boolwrapper2 = ValueWrapper(boolwrapper.value)
        assert_test(boolwrapper == boolwrapper2,"Test 25a")
        boolwrapper3= ValueWrapper(not boolwrapper.value)
        assert_test(boolwrapper == boolwrapper2,"Test 25b")

        boolwrapper = ValueWrapper(0)
        boolwrapper2 = ValueWrapper(1)
        bwf = BooleanRequirement(boolwrapper)
        bwt = BooleanRequirement(boolwrapper2)

        assert_test(bwt.match(None), "Test 25c")
        assert_test(not bwf.match(None), "Test 25d")

        

        def check(tuples, id_list, must_exist=True):
            ids_in_tuples = {t[0] for t in tuples}
            if must_exist:
                return all(id_ in ids_in_tuples for id_ in id_list)
            else:
                return not any(id_ in ids_in_tuples for id_ in id_list)


        # One off Claims Testing
        manager.clearRequirements()
        assert_test(not manager.hasClaims(), "Test 26")

        required_ids =  [all_ops[0].id, all_ops[-1].id]

        for id in required_ids:
            manager.addRequirements(IDRequirement(id))

        assert_test(manager.hasClaims(), "Test 27")

        # Add some 'unknown' ID
        manager.addRequirements(IDRequirement('SOME UNKOWN ID'))

        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == 2, "Test 28")

        assert_test(check(matched_opportunities,required_ids), "Test 29")
        
        manager.removeOneOffClaims()
        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == 0, "Test 30")



        requirement = NoticeRequirement(200,TypeRequirement('EXTRA_TIME',MinTimeRequirement(180,PeriodRequirement(str(yesterday), str(tomorrow)))))

        assert_test(not requirement.match(Opportunity({'due_to_start':199,'duration':180, 'type':'EXTRA_TIME','date':str(today)})),"Test 31")
        assert_test(not requirement.match(Opportunity({'due_to_start':200,'duration':179, 'type':'EXTRA_TIME','date':str(yesterday)})), "Test 32")
        assert_test(not requirement.match(Opportunity({'due_to_start':344,'duration':180, 'type':'EXTRA_TIME','date':str(two_days_ago)})), "Test 33")
        assert_test(not requirement.match(Opportunity({'due_to_start':344,'duration':180, 'type':'EXTRA_TIME','date':str(seven_days_from_now)})), "Test 34")

        manager.clearRequirements()

        excludeRequirement = ExcludePeriodRequirement(*get_working_week_dates(str(today)))
        manager.addRequirements(excludeRequirement)
        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == 0, "Test 35")

        manager.clearRequirements()
    
        includeRequirement = PeriodRequirement(*get_working_week_dates(str(today)))
        manager.addRequirements(includeRequirement)
        matched_opportunities = manager.extract_matched_opportunties(all_ops)
        assert_test(len(matched_opportunities) == len(all_ops), "Test 36")


        requirement = NoticeRequirement(200,DayRequirement(0,TypeRequirement('EXTRA_TIME',MinTimeRequirement(180,PeriodRequirement(str(yesterday), str(seven_days_from_now))))))
        assert_test(not requirement.match(Opportunity({'due_to_start':400,'duration':180, 'type':'EXTRA_TIME','date':str(today)})),"Test 37")
        assert_test(not requirement.match(Opportunity({'due_to_start':800,'duration':200, 'type':'EXTRA_TIME','date':str(today)})),"Test 38")

        streq1 = StartTimeRequirement("0[5-6]:**")
        streq2 = StartTimeRequirement("0[5-6]:**")
        streq3 = StartTimeRequirement("0[5-6]:00")

        assert_test(streq1 == streq2, "Test 39")
        assert_test(not (streq1 == streq3), "Test 40")

        assert_test(not streq1.match(Opportunity({'start':"03:00:00   "})), "Test 41")
        assert_test(not streq1.match(Opportunity({'start':"04:00"})), "Test 42")
        assert_test(streq1.match(Opportunity({'start':"05:00"})), "Test 43")
        assert_test(streq1.match(Opportunity({'start':"06:59"})), "Test 44")
        assert_test(streq1.match(Opportunity({'start':"06:59:00    "})), "Test 45")
        assert_test(streq1.match(Opportunity({'start':"06:00"})), "Test 46")

        assert_test(not streq1.match(Opportunity({'start':"00:00"})), "Test 47")
        assert_test(not streq1.match(Opportunity({'start':"00:01"})), "Test 48")
        assert_test(not streq1.match(Opportunity({'start':"00:02"})), "Test 49")
        assert_test(not streq1.match(Opportunity({'start':"00:03"})), "Test 50")
        assert_test(not streq1.match(Opportunity({'start':"00:04"})), "Test 51")

        assert_test(not streq1.match(Opportunity({'start':"07:00"})), "Test 52")
        assert_test(not streq1.match(Opportunity({'start':"08:00"})), "Test 53")
        assert_test(not streq1.match(Opportunity({'start':"09:00"})), "Test 54")
        assert_test(not streq1.match(Opportunity({'start':"10:00"})), "Test 55")
        assert_test(streq1.match(Opportunity({'start':"05:01"})), "Test 56")
        assert_test(streq2.match(Opportunity({'start':"05:01"})), "Test 57")



        # Test instance claim removeval
        manager = RequirementsManager()
        id1 = IDRequirement("A123")
        id2 = IDRequirement("B456")
        id3 = IDRequirement("C789")

        manager.addRequirements(id1)
        manager.addRequirements(id2)
        manager.addRequirements(id3)

        manager.addRequirements(vet_requirement)
        logging.info(f"manager: {manager}")

        manager.removeOneOffIDClaimsThatMatch([(id2.id, "TIME_OFF")])

        assert_test(id1 in  manager.requirements, "Test 58")
        assert_test(id2 not in  manager.requirements, "Test 59")
        assert_test(id3 in  manager.requirements, "Test 60")
        assert_test(vet_requirement in  manager.requirements, "Test 61")

        
        return tested, tests_success, tests_failed 




    try:
        #logging.basicConfig(format='%(name)s %(levelname)s: %(asctime)s: %(message)s', level=logging.INFO)
        tested, tests_success, tests_failed = test(False)
        print(f"************ {'PASS' if tests_failed == 0 else 'FAIL'}: COMPLETED: {tested} PASSED: {tests_success} FAILED: {tests_failed} ***************")
        exit(0)
    except Exception as e:
        print(f"************ FAIL *************** {e}")
        exit(1)


