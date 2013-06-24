/*
 * TestsF.cpp
 *
 *  Created on: 25/05/2013
 *      Author: ben
 *  Tests for the functional Employee class
 */

#include "EmployeeF.h"
#include <gtest/gtest.h>

TEST(EmployeeF,BasicTests) {
	// Create a simple employee instance
	const EmployeeF e("Ben","Last",1,1000.0);

	//Verify values
	ASSERT_EQ(e.GivenName(),"Ben");
	ASSERT_EQ(e.FamilyName(),"Last");
	ASSERT_EQ(e.Number(),1);
	ASSERT_EQ(e.Salary(),1000.0);

	//Change values and verify the changes
	const EmployeeF e2 = e.SetNumber(123);
	ASSERT_EQ(e2.Number(),123);
	ASSERT_NE(e.Number(),e2.Number());
}
