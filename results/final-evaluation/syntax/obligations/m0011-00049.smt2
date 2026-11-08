(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x6838 (and (distinct i_2 (_ bv0 4)) true)))
(not $x6838)))
(check-sat)
