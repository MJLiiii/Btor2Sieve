(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x5066 (and (distinct i_2 (_ bv0 4)) true)))
(not $x5066)))
(check-sat)
