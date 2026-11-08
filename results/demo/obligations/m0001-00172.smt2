(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x132 (and (distinct i_8 (_ bv0 4)) true)))
(not $x132)))
(check-sat)
