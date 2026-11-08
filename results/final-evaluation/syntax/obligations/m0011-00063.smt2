(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2246 (and (distinct i_2 (_ bv15 4)) true)))
(not $x2246)))
(check-sat)
