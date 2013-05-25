//A non-functional Employee class

#include <string>

class EmployeeNF {
public:
	EmployeeNF(const std::string& aGivenName,
			   const std::string& aFamilyName,
			   const int	aNumber,
			   const double &aSalary) :
				   givenName(aGivenName),
				   familyName(aFamilyName),
				   number(aNumber),
				   salary(aSalary)
	{}

	void SetNumber(const int aNumber) {
		number=aNumber;
	}

	int Number() {
		return number;
	}

	void SetSalary(const double& aSalary) {
		salary=aSalary;
	}

	double Salary() {
		return salary;
	}

	void SetGivenName(const std::string& aGivenName) {
		givenName=aGivenName;
	}

	std::string GivenName() {
		return givenName;
	}

	void SetFamilyName(const std::string& aFamilyName) {
		familyName=aFamilyName;
	}

	std::string FamilyName() {
		return familyName;
	}

private:
	std::string	givenName;
	std::string	familyName;
	int			number;
	double		salary;
};
