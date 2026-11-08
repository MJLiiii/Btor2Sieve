(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 1))
(assert
 (and true true))
(assert
 (let (($x39 (and (distinct i_2 (_ bv0 1)) true)))
(not $x39)))
(check-sat)
