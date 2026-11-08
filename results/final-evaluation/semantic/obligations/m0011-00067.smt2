(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x3118 (and (distinct i_2 (_ bv8 4)) true)))
(not $x3118)))
(check-sat)
