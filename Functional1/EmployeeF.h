//An immutable Employee class

#include <string>

class EmployeeF {
public:
	//The constructor body is in EmployeeF.cpp so that
	//there's something for the linker to use.
	EmployeeF(const std::string& aGivenName,
			  const std::string& aFamilyName,
			  const int	aNumber,
			  const double &aSalary);

	const int& Number() const {
		return number;
	}

	const EmployeeF SetNumber(const int aNumber) const {
		return EmployeeF(givenName,
						 familyName,
						 aNumber,
						 salary);
	}

	const double& Salary() const {
		return salary;
	}

	const EmployeeF SetSalary(const double& aSalary) const {
		return EmployeeF(givenName,
						 familyName,
						 number,
						 aSalary);
	}

	const std::string& GivenName() const {
		return givenName;
	}

	const std::string& FamilyName() const {
		return familyName;
	}

private:
	const std::string	givenName;
	const std::string	familyName;
	const int			number;
	const double		salary;
};
